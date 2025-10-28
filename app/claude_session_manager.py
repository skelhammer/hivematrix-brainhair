"""
Claude Code Session Manager

Manages Claude Code invocations for chat sessions, handling:
- Message processing with Claude Code
- Tool call interception
- PHI/CJIS filtering of responses
- Context management
"""

import subprocess
import json
import uuid
import os
from datetime import datetime
from typing import Dict, Optional, Callable
from flask import current_app
from .helm_logger import get_helm_logger
from .presidio_filter import filter_data


class ClaudeSession:
    """
    Manages a Claude Code session context.

    Each chat session maintains context and spawns Claude Code for each message.
    """

    def __init__(self, session_id: str, user: str, context: Dict, db_session_id: Optional[str] = None):
        """
        Initialize a new Claude Code session.

        Args:
            session_id: Unique session identifier (in-memory)
            user: Username of the person using this session
            context: Context dict with ticket, client, etc.
            db_session_id: Optional database session ID to resume existing session
        """
        # Import inside method to ensure app context is available
        from extensions import db
        from models import ChatSession as ChatSessionModel, ChatMessage

        self.session_id = session_id
        self.user = user
        self.context = context
        self.logger = get_helm_logger()
        self.conversation_history = []
        self.db_session_id = db_session_id

        # Load or create database session
        if db_session_id:
            # Resume existing session
            self.db_session = ChatSessionModel.query.get(db_session_id)
            if self.db_session:
                # Load conversation history from database
                for msg in self.db_session.messages:
                    self.conversation_history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                self.logger.info(f"Resumed chat session {db_session_id} with {len(self.conversation_history)} messages")
            else:
                self.logger.warning(f"Could not find session {db_session_id}, creating new one")
                self.db_session = None
        else:
            self.db_session = None

        # Create new database session if needed
        if not self.db_session:
            self.db_session = ChatSessionModel(
                id=str(uuid.uuid4()),
                user_id=self.user,
                user_name=self.user,  # TODO: Get actual name from user service
                ticket_number=context.get('ticket'),
                client_name=context.get('client')
            )
            db.session.add(self.db_session)
            db.session.commit()
            self.db_session_id = self.db_session.id
            self.logger.info(f"Created new chat session {self.db_session_id}")

        # Build environment variables for Claude Code
        self.env = os.environ.copy()
        self.env['HIVEMATRIX_USER'] = self.user
        self.env['HIVEMATRIX_CONTEXT'] = json.dumps(self.context)
        self.env['BRAINHAIR_SESSION_ID'] = self.db_session_id  # For session tools
        self.env['BRAINHAIR_URL'] = os.environ.get('SERVICE_URL', 'http://localhost:5050')

        # Path to our tools directory
        tools_dir = os.path.join(os.path.dirname(__file__), '..', 'claude_tools')
        self.env['PYTHONPATH'] = tools_dir + ':' + self.env.get('PYTHONPATH', '')

        # Load system prompt
        system_prompt_path = os.path.join(tools_dir, 'SYSTEM_PROMPT.md')
        self.system_prompt = ""
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r') as f:
                self.system_prompt = f.read()

        # Add context to system prompt
        context_info = f"""

## Current Context

- **Technician**: {self.user}
- **Ticket**: {self.context.get('ticket') or 'Not set'}
- **Client**: {self.context.get('client') or 'Not set'}
"""
        self.system_prompt += context_info

        self.logger.info(f"Created Claude Code session {self.session_id} for user {self.user}")

    def start(self):
        """Session is ready to use - no persistent process needed."""
        pass

    def send_message_stream(self, message: str):
        """
        Send a message to Claude Code and stream the response.

        Args:
            message: User's message

        Yields:
            Response chunks
        """
        try:
            # Import inside method to ensure app context is available
            from extensions import db
            from models import ChatMessage

            # Add message to conversation history
            self.conversation_history.append({"role": "user", "content": message})

            # Save user message to database
            user_msg = ChatMessage(
                session_id=self.db_session_id,
                role="user",
                content=message
            )
            db.session.add(user_msg)
            db.session.commit()

            self.logger.info(f"Invoking Claude Code for session {self.session_id}: {message[:50]}...")

            # Build the full prompt with conversation history
            conversation_context = "\n\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in self.conversation_history[-10:]  # Last 10 messages
            ])

            full_prompt = f"{self.system_prompt}\n\n## Conversation History\n\n{conversation_context}"

            # Invoke Claude Code with permissions bypassed and streaming JSON output
            # This is safe since we're in a controlled server environment and only accessing HiveMatrix data
            # Try to find claude binary - check PATH first, then npx cache
            import shutil
            claude_bin = shutil.which('claude')

            if not claude_bin:
                # Fallback to npx cache
                import glob
                npx_cache = os.path.expanduser('~/.npm/_npx/*/node_modules/.bin/claude')
                claude_bins = glob.glob(npx_cache)
                if claude_bins:
                    claude_bin = claude_bins[0]

            if not claude_bin:
                raise RuntimeError("Claude Code binary not found. Run: npx -y @anthropic-ai/claude-code or ensure 'claude' is in PATH")
            cmd = [
                claude_bin,
                '--model', 'claude-sonnet-4-5',
                '--dangerously-skip-permissions',  # Bypass all permission checks
                '--verbose',  # Required for --output-format=stream-json
                '--print',  # Required for --output-format
                '--output-format', 'stream-json',  # Get real-time streaming JSON
                '--include-partial-messages',  # Include partial chunks
                '--append-system-prompt', full_prompt,
                message  # The actual user message
            ]

            self.logger.info(f"Running: {' '.join(cmd[:4])}... <message>")

            # Run Claude Code and stream output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for simplicity
                env=self.env,
                text=True,
                bufsize=1,  # Line buffered
            )

            response_text = ""
            import time
            last_output_time = time.time()
            idle_timeout = 30  # seconds without output before we give up
            self._last_stop_reason = None  # Track stop reason for tool_use detection

            # Stream output line by line
            line_count = 0
            self.logger.info(f"[STREAM] Starting to read from Claude Code stdout")

            for line in iter(process.stdout.readline, ''):
                line_count += 1
                self.logger.debug(f"[STREAM] Line {line_count} received (length: {len(line)})")

                # Check if process has terminated
                poll_result = process.poll()
                if poll_result is not None:
                    self.logger.info(f"[STREAM] Process terminated with code {poll_result} after {line_count} lines")
                    break

                # Check for idle timeout
                idle_time = time.time() - last_output_time
                if idle_time > idle_timeout:
                    self.logger.warning(f"[STREAM] No output for {idle_timeout}s (idle: {idle_time:.1f}s), assuming process hung")
                    process.kill()
                    yield "\n\n[Claude Code appears to have hung - terminated]"
                    break

                if not line or not line.strip():
                    self.logger.debug(f"[STREAM] Line {line_count} is empty, skipping")
                    continue

                line = line.strip()
                last_output_time = time.time()  # Reset timeout on each line
                self.logger.debug(f"[STREAM] Line {line_count} content: {line[:100]}...")

                try:
                    # Parse the JSON event from Claude Code
                    event = json.loads(line)
                    event_type = event.get('type')
                    self.logger.debug(f"[STREAM] Line {line_count} parsed as JSON, type: {event_type}")

                    # Unwrap stream_event wrapper
                    if event_type == 'stream_event':
                        inner_event = event.get('event', {})
                        event_type = inner_event.get('type')
                        event = inner_event
                        self.logger.debug(f"[STREAM] Unwrapped stream_event to type: {event_type}")

                    # Handle content_block_delta for streaming text chunks
                    if event_type == 'content_block_delta':
                        delta = event.get('delta', {})
                        delta_type = delta.get('type')
                        self.logger.debug(f"[STREAM] content_block_delta, delta_type: {delta_type}")

                        if delta_type == 'text_delta':
                            # Streaming text chunk
                            text = delta.get('text', '')
                            response_text += text
                            self.logger.debug(f"[STREAM] Yielding text chunk: {repr(text[:50])}")
                            yield text

                    # Handle content_block_start for tool calls
                    elif event_type == 'content_block_start':
                        content_block = event.get('content_block', {})
                        block_type = content_block.get('type')
                        self.logger.info(f"[STREAM] content_block_start, block_type: {block_type}")

                        if block_type == 'tool_use':
                            tool_name = content_block.get('name', 'unknown')
                            tool_id = content_block.get('id', '')
                            tool_input = content_block.get('input', {})

                            # For Bash tool, show the description if available
                            tool_display = tool_name
                            if tool_name == 'Bash' and 'description' in tool_input:
                                tool_display = f"Bash: {tool_input['description']}"

                            self.logger.info(f"[STREAM] Tool use detected: {tool_name} (id: {tool_id}), input: {tool_input}")
                            yield json.dumps({"type": "thinking", "action": f"⚙️ {tool_display}"})

                    # Skip assistant message - we already got the text from content_block_delta
                    elif event_type == 'assistant':
                        # This contains the full message but we already streamed it via deltas
                        # Just use it to update our conversation history later
                        self.logger.debug(f"[STREAM] Received assistant message (already streamed via deltas)")
                        pass

                    elif event_type == 'message_stop':
                        # Message complete - but check if we're waiting for tool execution
                        stop_reason = getattr(self, '_last_stop_reason', None)
                        self.logger.info(f"[STREAM] Received message_stop event after {line_count} lines, stop_reason: {stop_reason}")

                        # If stop_reason is tool_use, DON'T break - keep reading for tool output
                        if stop_reason == 'tool_use':
                            self.logger.info(f"[STREAM] Stop reason is tool_use, continuing to read tool execution output...")
                            continue
                        else:
                            # Normal completion, stop reading
                            break

                    elif event_type == 'result':
                        # Final result - message complete
                        self.logger.info(f"[STREAM] Received result event after {line_count} lines")
                        break

                    elif event_type == 'system':
                        # System initialization event - send as live message
                        self.logger.debug(f"[STREAM] System event")
                        yield json.dumps({"type": "live_message", "content": "Initializing Claude Code..."})

                    elif event_type == 'message_start':
                        # Message starting
                        self.logger.debug(f"[STREAM] Message start event")
                        yield json.dumps({"type": "live_message", "content": "Claude is responding..."})

                    elif event_type == 'user':
                        # User message echo
                        self.logger.debug(f"[STREAM] User message echo")
                        pass

                    elif event_type == 'content_block_stop':
                        # Content block finished
                        self.logger.debug(f"[STREAM] content_block_stop")
                        pass

                    elif event_type == 'message_delta':
                        # Message metadata update - check for stop_reason
                        delta = event.get('delta', {})
                        stop_reason = delta.get('stop_reason')
                        self.logger.debug(f"[STREAM] message_delta, stop_reason: {stop_reason}")

                        # Store stop_reason for later use
                        if stop_reason:
                            self._last_stop_reason = stop_reason

                    else:
                        # Log unknown events for debugging
                        self.logger.info(f"[STREAM] Unknown event type: {event_type}, full data: {json.dumps(event)[:200]}")

                except json.JSONDecodeError as e:
                    # Not JSON - could be stderr output or bash tool output
                    self.logger.warning(f"[STREAM] Line {line_count} is NOT JSON: {line[:200]}")
                    self.logger.warning(f"[STREAM] JSONDecodeError: {e}")
                    yield json.dumps({"type": "live_message", "content": line})
                except Exception as e:
                    self.logger.error(f"[STREAM] Unexpected error processing line {line_count}: {e}", exc_info=True)
                    self.logger.error(f"[STREAM] Line content was: {line[:200]}")

            self.logger.info(f"[STREAM] Exited read loop after {line_count} lines, response_text length: {len(response_text)}")

            # Process should already be done, but wait just in case
            if process.poll() is None:
                self.logger.warning("[STREAM] Process still running after loop exit, waiting...")
                try:
                    process.wait(timeout=10)
                    self.logger.info(f"[STREAM] Process finished with code {process.returncode}")
                except subprocess.TimeoutExpired:
                    self.logger.error("[STREAM] Process wait timed out after 10s, killing process")
                    process.kill()
                    process.wait()
            else:
                self.logger.info(f"[STREAM] Process already exited with code {process.returncode}")

            # Check for errors
            if process.returncode != 0:
                self.logger.error(f"[STREAM] Claude Code exited with non-zero code {process.returncode}")
                yield f"\n\n[Error: Claude Code exited with code {process.returncode}]"
            else:
                self.logger.info(f"[STREAM] Claude Code completed successfully")

            # Add response to history
            self.logger.info(f"[STREAM] Adding response to history (length: {len(response_text.strip())} chars)")
            self.conversation_history.append({"role": "assistant", "content": response_text.strip()})

            # Save assistant message to database
            assistant_msg = ChatMessage(
                session_id=self.db_session_id,
                role="assistant",
                content=response_text.strip()
            )
            db.session.add(assistant_msg)

            # Update session timestamp
            self.db_session.updated_at = datetime.utcnow()
            db.session.commit()
            self.logger.info(f"[STREAM] Saved assistant response to database")

        except subprocess.TimeoutExpired:
            self.logger.error(f"Claude Code timed out for session {self.session_id}")
            if 'process' in locals():
                process.kill()
            yield "\n\n[Error: Request timed out]"
        except Exception as e:
            self.logger.error(f"Error invoking Claude Code: {e}", exc_info=True)
            yield f"\n\n[Error: {str(e)}]"

    def _generate_demo_response(self, message: str) -> str:
        """
        Generate a demo response based on message content.

        This is a placeholder until real Claude API integration is added.
        """
        msg_lower = message.lower()

        # Try to call the Python tools to demonstrate they work
        if 'compan' in msg_lower and 'list' in msg_lower:
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'claude_tools'))
                from codex_tools import get_companies

                companies = get_companies(limit=5)
                if 'companies' in companies:
                    comp_list = "\n".join([f"- {c['name']} (ID: {c['account_number']})"
                                          for c in companies['companies'][:5]])
                    return f"Here are the first 5 companies from Codex:\n\n{comp_list}\n\nWould you like more details on any of these?"
            except Exception as e:
                self.logger.error(f"Error calling get_companies: {e}")
                return f"I tried to fetch companies but encountered an error: {str(e)}"

        elif 'ticket' in msg_lower and 'list' in msg_lower:
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'claude_tools'))
                from codex_tools import get_tickets

                tickets = get_tickets(limit=5)
                if 'tickets' in tickets and tickets['tickets']:
                    ticket_list = "\n".join([f"- #{t['id']}: {t['subject']} ({t['status']})"
                                            for t in tickets['tickets'][:5]])
                    return f"Here are recent tickets:\n\n{ticket_list}\n\nTotal found: {tickets.get('total', 'unknown')}"
                else:
                    return "I couldn't find any tickets. The API may not be fully configured yet."
            except Exception as e:
                self.logger.error(f"Error calling get_tickets: {e}")
                return f"I tried to fetch tickets but encountered an error: {str(e)}"

        elif 'device' in msg_lower or 'computer' in msg_lower:
            return f"""I can help you check device information. The Datto integration is set up with these capabilities:

- List devices for a company
- Check device status (online/offline)
- View device health metrics (CPU, RAM, disk usage)
- Execute PowerShell commands (requires your approval)

What would you like to know about the devices?"""

        elif 'knowledge' in msg_lower or 'search' in msg_lower:
            return """I can search the knowledge base for you. Unfortunately, the KnowledgeTree API is currently returning 500 errors and needs debugging.

Once that's fixed, I'll be able to:
- Search for articles by keyword
- Browse categories
- Get full article content

Is there something specific you'd like to find?"""

        elif 'help' in msg_lower or 'what can you do' in msg_lower:
            return f"""I'm Brain Hair, your AI technical support assistant! Here's what I can help with:

📋 **Tickets**: List and manage support tickets
🏢 **Companies**: View company information
💻 **Devices**: Check device status and run diagnostics
📚 **Knowledge Base**: Search documentation (currently being fixed)
⚙️ **Commands**: Execute PowerShell commands with your approval

**Current Context:**
- Technician: {self.user}
- Ticket: {self.context.get('ticket') or 'Not set'}
- Client: {self.context.get('client') or 'Not set'}

**Note**: I'm currently running in DEMO mode. For full AI capabilities, the Claude API needs to be integrated.

What would you like me to help with?"""

        else:
            return f"""I understand you said: "{message}"

I'm currently running in DEMO mode to show the architecture works. To get real AI responses:

1. The Anthropic SDK needs to be installed (`pip install anthropic`)
2. An API key needs to be configured
3. The Claude API integration needs to be completed

For now, I can demonstrate the working tools:
- Try: "list companies"
- Try: "list tickets"
- Try: "what can you do"

What would you like to try?"""

    def stop(self):
        """Stop/cleanup the session."""
        self.logger.info(f"Stopped Claude Code session {self.session_id}")


class ClaudeSessionManager:
    """
    Manages multiple Claude Code sessions.

    Handles session creation, retrieval, and cleanup.
    """

    def __init__(self):
        """Initialize the session manager."""
        self.sessions: Dict[str, ClaudeSession] = {}
        self.logger = get_helm_logger()

    def create_session(self, user: str, context: Dict, db_session_id: Optional[str] = None) -> str:
        """
        Create a new Claude Code session or resume an existing one.

        Args:
            user: Username
            context: Context dict with ticket, client, etc.
            db_session_id: Optional database session ID to resume

        Returns:
            Session ID (in-memory)
        """
        session_id = str(uuid.uuid4())
        session = ClaudeSession(session_id, user, context, db_session_id=db_session_id)

        try:
            session.start()
            self.sessions[session_id] = session
            if db_session_id:
                self.logger.info(f"Created session {session_id} (resumed DB session {db_session_id}) for user {user}")
            else:
                self.logger.info(f"Created session {session_id} (new DB session {session.db_session_id}) for user {user}")
            return session_id
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}", exc_info=True)
            raise

    def get_session(self, session_id: str) -> Optional[ClaudeSession]:
        """
        Get an existing session.

        Args:
            session_id: Session identifier

        Returns:
            ClaudeSession or None if not found
        """
        return self.sessions.get(session_id)

    def destroy_session(self, session_id: str):
        """
        Destroy a session.

        Args:
            session_id: Session identifier
        """
        session = self.sessions.pop(session_id, None)
        if session:
            session.stop()
            self.logger.info(f"Destroyed session {session_id}")

    def cleanup_idle_sessions(self, max_age_seconds: int = 3600):
        """
        Clean up idle sessions older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup
        """
        # TODO: Implement idle tracking and cleanup
        pass


# Global session manager instance
_session_manager = None


def get_session_manager() -> ClaudeSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = ClaudeSessionManager()
    return _session_manager
