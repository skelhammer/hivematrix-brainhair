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
import time
from datetime import datetime
from typing import Dict, Optional, Callable
from flask import current_app
from .helm_logger import get_helm_logger
from .presidio_filter import filter_data


def _get_user_display_name(user_id: str) -> str:
    """
    Get user's display name from Core service.

    Args:
        user_id: User ID (from JWT sub claim)

    Returns:
        Display name if found, otherwise returns user_id
    """
    try:
        from .service_client import call_service
        # Try to get user info from Core
        response = call_service('core', f'/api/users/{user_id}')
        if response.status_code == 200:
            user_data = response.json()
            # Try various name fields
            return (user_data.get('display_name') or
                    user_data.get('full_name') or
                    user_data.get('name') or
                    user_id)
    except Exception as e:
        # Log error but don't fail - fallback to user_id
        import logging
        logging.getLogger(__name__).debug(f"Could not fetch user display name: {e}")

    return user_id


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
        self.current_process = None  # Track running Claude Code process
        self.last_activity = time.time()  # Track last activity for idle cleanup

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
            # Get user's display name from Core service
            user_display_name = _get_user_display_name(self.user)

            self.db_session = ChatSessionModel(
                id=str(uuid.uuid4()),
                user_id=self.user,
                user_name=user_display_name,
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

        # Add pyenv Python to PATH so AI tools use it
        project_root = os.path.dirname(os.path.dirname(__file__))
        pyenv_bin = os.path.join(project_root, 'pyenv', 'bin')
        if os.path.exists(pyenv_bin):
            self.env['PATH'] = pyenv_bin + ':' + self.env.get('PATH', '')

        # Path to our tools directory
        tools_dir = os.path.join(os.path.dirname(__file__), '..', 'claude_tools')
        self.env['PYTHONPATH'] = tools_dir + ':' + self.env.get('PYTHONPATH', '')

        # Load system prompt
        system_prompt_path = os.path.join(tools_dir, 'SYSTEM_PROMPT.md')
        self.system_prompt = ""
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r') as f:
                self.system_prompt = f.read()

        # Add available AI tools to system prompt
        ai_tools_info = self._discover_ai_tools()
        if ai_tools_info:
            self.system_prompt += f"\n\n{ai_tools_info}"

        # Add context to system prompt
        context_info = f"""

## Current Context

- **Technician**: {self.user}
- **Ticket**: {self.context.get('ticket') or 'Not set'}
- **Client**: {self.context.get('client') or 'Not set'}
"""
        self.system_prompt += context_info

        self.logger.info(f"Created Claude Code session {self.session_id} for user {self.user}")

    def _discover_ai_tools(self):
        """Discover available AI tools and generate documentation."""
        ai_tools_dir = os.path.join(os.path.dirname(__file__), '..', 'ai_tools')

        if not os.path.exists(ai_tools_dir):
            return ""

        tools_doc = ["## 🔧 Available AI Tools (Auto-Discovered)", ""]
        tools_doc.append(f"The following tools are available in `{os.path.abspath(ai_tools_dir)}`:")
        tools_doc.append("")

        # Scan for Python files
        tool_files = []
        for filename in sorted(os.listdir(ai_tools_dir)):
            if filename.endswith('.py') and not filename.startswith('_') and filename != 'approval_helper.py':
                tool_path = os.path.join(ai_tools_dir, filename)

                # Extract docstring from file
                try:
                    with open(tool_path, 'r') as f:
                        content = f.read()

                    # Extract first docstring
                    import re
                    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)

                    if docstring_match:
                        docstring = docstring_match.group(1).strip()
                        # Get first line (summary)
                        summary = docstring.split('\n')[0].strip()

                        # Extract IMPORTANT notes (for critical instructions)
                        important_notes = []
                        for line in docstring.split('\n'):
                            if 'IMPORTANT:' in line or line.strip().startswith('IMPORTANT'):
                                # Capture this line and following bullet points
                                important_notes.append(line.strip())
                            elif important_notes and (line.strip().startswith('-') or line.strip().startswith('•')):
                                important_notes.append(line.strip())
                            elif important_notes and line.strip() and not line.strip().startswith(('Usage:', 'Example:')):
                                important_notes.append(line.strip())
                            elif important_notes and not line.strip():
                                break  # End of important section

                        # Extract usage examples
                        usage_lines = []
                        in_usage = False
                        for line in docstring.split('\n'):
                            if 'Usage:' in line:
                                in_usage = True
                                continue
                            if in_usage:
                                if line.strip() and not line.strip().startswith('#'):
                                    if 'python' in line:
                                        usage_lines.append(line.strip())
                                if len(usage_lines) >= 2:  # Limit to 2 examples
                                    break

                        tool_files.append({
                            'name': filename,
                            'summary': summary,
                            'important': important_notes[:5] if important_notes else [],  # Up to 5 important lines
                            'usage': usage_lines[:2] if usage_lines else []
                        })
                except Exception as e:
                    # Skip files we can't parse
                    continue

        if not tool_files:
            return ""

        # Group tools by category
        categories = {
            'Billing & Plans': [],
            'Knowledge Management': [],
            'Companies & Tickets': [],
            'Network Equipment': [],
            'Other': []
        }

        for tool in tool_files:
            name = tool['name']
            if any(x in name for x in ['billing', 'plan', 'feature']):
                categories['Billing & Plans'].append(tool)
            elif 'knowledge' in name:
                categories['Knowledge Management'].append(tool)
            elif any(x in name for x in ['company', 'companies', 'ticket', 'device']):
                categories['Companies & Tickets'].append(tool)
            elif 'network' in name or 'equipment' in name:
                categories['Network Equipment'].append(tool)
            else:
                categories['Other'].append(tool)

        # Generate documentation
        for category, tools in categories.items():
            if tools:
                tools_doc.append(f"### {category}")
                tools_doc.append("")
                for tool in tools:
                    tools_doc.append(f"**{tool['name']}** - {tool['summary']}")

                    # Add important notes if present
                    if tool.get('important'):
                        tools_doc.append("")
                        for note in tool['important']:
                            tools_doc.append(note)
                        tools_doc.append("")

                    if tool['usage']:
                        tools_doc.append("```bash")
                        for usage in tool['usage']:
                            tools_doc.append(usage)
                        tools_doc.append("```")
                    tools_doc.append("")

        tools_doc.append("**Note:** All tools are pre-approved for data retrieval. Write operations require user approval via the approval dialog.")
        tools_doc.append("")

        return '\n'.join(tools_doc)

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
        # Update last activity timestamp
        self.last_activity = time.time()

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

            # Build the full prompt with conversation history
            conversation_context = "\n\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in self.conversation_history[-10:]  # Last 10 messages
            ])

            full_prompt = f"{self.system_prompt}\n\n## Conversation History\n\n{conversation_context}"

            # Invoke Claude Code with permissions bypassed and streaming JSON output
            # This is safe since we're in a controlled server environment and only accessing HiveMatrix data
            # Try to find claude binary - check common locations first, then PATH, then npx cache
            import shutil
            import glob

            claude_bin = None

            # Check common install locations first (handles systemd restricted PATH)
            common_locations = [
                os.path.expanduser('~/.local/bin/claude'),  # pip install / pipx
                '/usr/local/bin/claude',                     # system-wide install
                os.path.expanduser('~/.npm-global/bin/claude'),  # npm global
            ]

            for location in common_locations:
                if os.path.isfile(location) and os.access(location, os.X_OK):
                    claude_bin = location
                    break

            # Fall back to PATH lookup
            if not claude_bin:
                claude_bin = shutil.which('claude')

            # Fall back to npx cache
            if not claude_bin:
                npx_cache = os.path.expanduser('~/.npm/_npx/*/node_modules/.bin/claude')
                claude_bins = glob.glob(npx_cache)
                if claude_bins:
                    claude_bin = claude_bins[0]

            if not claude_bin:
                raise RuntimeError("Claude Code binary not found. Install with: npm install -g @anthropic-ai/claude-code, or ensure 'claude' is in ~/.local/bin or PATH")


            cmd = [
                claude_bin,
                '--model', 'claude-sonnet-4-5',
                '--allowed-tools', 'Bash Read Grep Glob WebFetch WebSearch',  # READ ONLY - Safe tools only
                '--permission-mode', 'dontAsk',  # Auto-approve safe operations
                '--verbose',  # Required for --output-format=stream-json
                '--print',  # Required for --output-format
                '--output-format', 'stream-json',  # Get real-time streaming JSON
                '--include-partial-messages',  # Include partial chunks
                '--append-system-prompt', full_prompt,
                message  # The actual user message
            ]


            # Run Claude Code and stream output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for simplicity
                env=self.env,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Store process reference for potential cancellation
            self.current_process = process

            response_text = ""
            last_output_time = time.time()
            idle_timeout = 120  # seconds without output before we give up (increased for tool operations)
            self._last_stop_reason = None  # Track stop reason for tool_use detection

            # Track current tool usage for displaying details
            current_tool = None
            current_tool_input = ""

            # Stream output line by line
            line_count = 0

            for line in iter(process.stdout.readline, ''):
                line_count += 1

                # Check if process has terminated
                poll_result = process.poll()
                if poll_result is not None:
                    break

                # Check for idle timeout
                idle_time = time.time() - last_output_time
                if idle_time > idle_timeout:
                    process.kill()
                    yield "\n\n[Claude Code appears to have hung - terminated]"
                    break

                if not line or not line.strip():
                    continue

                line = line.strip()
                last_output_time = time.time()  # Reset timeout on each line

                try:
                    # Parse the JSON event from Claude Code
                    event = json.loads(line)
                    event_type = event.get('type')

                    # Check if this is a custom approval request from a tool
                    if event_type == 'approval_request':
                        yield json.dumps(event)
                        continue

                    # Unwrap stream_event wrapper
                    if event_type == 'stream_event':
                        inner_event = event.get('event', {})
                        event_type = inner_event.get('type')
                        event = inner_event

                    # Handle content_block_delta for streaming text chunks
                    if event_type == 'content_block_delta':
                        delta = event.get('delta', {})
                        delta_type = delta.get('type')

                        if delta_type == 'text_delta':
                            # Streaming text chunk
                            text = delta.get('text', '')
                            response_text += text
                            yield text
                        elif delta_type == 'input_json_delta':
                            # Tool input streaming
                            partial_json = delta.get('partial_json', '')
                            current_tool_input += partial_json

                    # Handle content_block_start for tool calls
                    elif event_type == 'content_block_start':
                        content_block = event.get('content_block', {})
                        block_type = content_block.get('type')

                        if block_type == 'tool_use':
                            current_tool = content_block.get('name', 'unknown')
                            current_tool_input = ""  # Reset input accumulator
                            # Don't yield yet - wait for input to accumulate

                    # Skip assistant message - we already got the text from content_block_delta
                    elif event_type == 'assistant':
                        # This contains the full message but we already streamed it via deltas
                        # Just use it to update our conversation history later
                        pass

                    elif event_type == 'message_stop':
                        # Message complete - but check if we're waiting for tool execution
                        stop_reason = getattr(self, '_last_stop_reason', None)

                        # If stop_reason is tool_use, DON'T break - keep reading for tool output
                        if stop_reason == 'tool_use':
                            continue
                        else:
                            # Normal completion, stop reading
                            break

                    elif event_type == 'result':
                        # Final result - message complete
                        break

                    elif event_type == 'system':
                        # System initialization event - send as live message
                        yield json.dumps({"type": "live_message", "content": "Initializing Claude Code..."})

                    elif event_type == 'message_start':
                        # Message starting
                        yield json.dumps({"type": "live_message", "content": "Claude is responding..."})

                    elif event_type == 'user':
                        # User message echo
                        pass

                    elif event_type == 'content_block_stop':
                        # Content block finished - reset tool tracking
                        if current_tool:
                            current_tool = None
                            current_tool_input = ""


                    elif event_type == 'message_delta':
                        # Message metadata update - check for stop_reason
                        delta = event.get('delta', {})
                        stop_reason = delta.get('stop_reason')

                        # Store stop_reason for later use
                        if stop_reason:
                            self._last_stop_reason = stop_reason

                    else:
                        # Unknown event type - ignore
                        pass

                except json.JSONDecodeError:
                    # Not JSON - could be stderr output or bash tool output
                    yield json.dumps({"type": "live_message", "content": line})
                except Exception:
                    # Ignore other parsing errors
                    pass

            # Process should already be done, but wait just in case
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # Check for errors
            if process.returncode != 0:
                yield f"\n\n[Error: Claude Code exited with code {process.returncode}]"

            # Add response to history
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

        except subprocess.TimeoutExpired:
            self.logger.error(f"Claude Code timed out for session {self.session_id}")
            if 'process' in locals():
                process.kill()
            yield "\n\n[Error: Request timed out]"
        except Exception as e:
            self.logger.error(f"Error invoking Claude Code: {type(e).__name__}: {e}")
            yield f"\n\n[Error: Internal server error - {type(e).__name__}]"

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
                return "I tried to fetch companies but encountered an error. Please try again later."

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
                return "I tried to fetch tickets but encountered an error. Please try again later."

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

    def stop_current_response(self):
        """Stop the currently running Claude Code process if any."""
        if self.current_process and self.current_process.poll() is None:
            # Process is still running, kill it
            self.logger.info(f"Terminating Claude Code process for session {self.session_id}")
            import signal
            try:
                self.current_process.send_signal(signal.SIGTERM)
                # Wait briefly for graceful shutdown
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.logger.warning(f"Force killing Claude Code process for session {self.session_id}")
                    self.current_process.kill()
                    self.current_process.wait()
                self.logger.info(f"Successfully terminated Claude Code process for session {self.session_id}")
                return True
            except Exception as e:
                self.logger.error(f"Error terminating process: {e}")
                return False
        else:
            self.logger.info(f"No active process to stop for session {self.session_id}")
            return False

    def stop(self):
        """Stop/cleanup the session."""
        self.stop_current_response()
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
        self._cleanup_thread = None
        self._cleanup_stop_event = None
        self._start_cleanup_thread()

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
            self.logger.error(f"Failed to create session: {e}")
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

    def cleanup_idle_sessions(self, max_age_seconds: int = 1800):
        """
        Clean up idle sessions older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds before cleanup (default: 30 minutes)
        """
        import time
        current_time = time.time()
        sessions_to_cleanup = []

        # Find idle sessions
        for session_id, session in self.sessions.items():
            idle_time = current_time - session.last_activity
            if idle_time > max_age_seconds:
                sessions_to_cleanup.append(session_id)
                self.logger.info(
                    f"Session {session_id} idle for {int(idle_time)}s, marking for cleanup"
                )

        # Clean up idle sessions
        for session_id in sessions_to_cleanup:
            self.destroy_session(session_id)

        if sessions_to_cleanup:
            self.logger.info(f"Cleaned up {len(sessions_to_cleanup)} idle session(s)")

        return len(sessions_to_cleanup)

    def _start_cleanup_thread(self):
        """Start background thread for periodic session cleanup."""
        import threading
        self._cleanup_stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        self.logger.info("Started session cleanup background thread")

    def _cleanup_loop(self):
        """Background loop that runs cleanup periodically."""
        import time
        cleanup_interval = 300  # Run cleanup every 5 minutes

        while not self._cleanup_stop_event.is_set():
            try:
                # Wait for the interval or stop event
                if self._cleanup_stop_event.wait(timeout=cleanup_interval):
                    break  # Stop event was set

                # Run cleanup (30 minute idle timeout)
                self.cleanup_idle_sessions(max_age_seconds=1800)

            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

        self.logger.info("Session cleanup thread stopped")

    def shutdown(self):
        """Shutdown the session manager and cleanup thread."""
        if self._cleanup_stop_event:
            self._cleanup_stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

        # Destroy all remaining sessions
        for session_id in list(self.sessions.keys()):
            self.destroy_session(session_id)

        self.logger.info("Session manager shutdown complete")


# Global session manager instance
_session_manager = None


def get_session_manager() -> ClaudeSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = ClaudeSessionManager()
    return _session_manager
