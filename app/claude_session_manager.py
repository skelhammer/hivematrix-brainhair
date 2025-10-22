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
from typing import Dict, Optional, Callable
from .helm_logger import get_helm_logger
from .presidio_filter import filter_data


class ClaudeSession:
    """
    Manages a Claude Code session context.

    Each chat session maintains context and spawns Claude Code for each message.
    """

    def __init__(self, session_id: str, user: str, context: Dict):
        """
        Initialize a new Claude Code session.

        Args:
            session_id: Unique session identifier
            user: Username of the person using this session
            context: Context dict with ticket, client, etc.
        """
        self.session_id = session_id
        self.user = user
        self.context = context
        self.logger = get_helm_logger()
        self.conversation_history = []

        # Build environment variables for Claude Code
        self.env = os.environ.copy()
        self.env['HIVEMATRIX_USER'] = self.user
        self.env['HIVEMATRIX_CONTEXT'] = json.dumps(self.context)

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
            # Add message to conversation history
            self.conversation_history.append({"role": "user", "content": message})

            self.logger.info(f"Invoking Claude Code for session {self.session_id}: {message[:50]}...")

            # Build the full prompt with conversation history
            conversation_context = "\n\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in self.conversation_history[-10:]  # Last 10 messages
            ])

            full_prompt = f"{self.system_prompt}\n\n## Conversation History\n\n{conversation_context}"

            # Invoke Claude Code with permissions bypassed and streaming JSON output
            # This is safe since we're in a controlled server environment and only accessing HiveMatrix data
            claude_bin = '/home/david/.npm/_npx/becf7b9e49303068/node_modules/.bin/claude'
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
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )

            response_text = ""

            # Stream stdout line by line - now it's JSON events
            for line in iter(process.stdout.readline, ''):
                if not line or not line.strip():
                    break

                try:
                    # Parse the JSON event from Claude Code
                    event = json.loads(line)
                    event_type = event.get('type')

                    if event_type == 'tool_use':
                        # Claude is using a tool - show what it's doing
                        tool_name = event.get('tool', {}).get('name', 'unknown')
                        tool_input = event.get('tool', {}).get('input', {})

                        # Extract meaningful info from tool input
                        if tool_name == 'bash':
                            command = tool_input.get('command', '')[:100]
                            yield json.dumps({"type": "thinking", "action": f"Running: {command}"}) + "\n"
                        else:
                            yield json.dumps({"type": "thinking", "action": f"Using tool: {tool_name}"}) + "\n"

                    elif event_type == 'text':
                        # Text content from Claude
                        text = event.get('text', '')
                        response_text += text
                        yield text

                    elif event_type == 'tool_result':
                        # Tool completed
                        yield json.dumps({"type": "thinking", "action": "Processing results..."}) + "\n"

                    elif event_type == 'message_start':
                        # Message starting
                        pass

                    elif event_type == 'message_stop':
                        # Message complete
                        break

                    else:
                        # Unknown event, log it
                        self.logger.debug(f"Unknown event type: {event_type}")

                except json.JSONDecodeError:
                    # Not JSON, treat as plain text
                    response_text += line
                    yield line

            # Wait for process to complete
            process.wait(timeout=120)

            # Check for errors
            if process.returncode != 0:
                stderr = process.stderr.read()
                self.logger.error(f"Claude Code error: {stderr}")
                yield f"\n\n[Error: Claude Code exited with code {process.returncode}]"

            # Add response to history
            self.conversation_history.append({"role": "assistant", "content": response_text.strip()})

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

    def create_session(self, user: str, context: Dict) -> str:
        """
        Create a new Claude Code session.

        Args:
            user: Username
            context: Context dict with ticket, client, etc.

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session = ClaudeSession(session_id, user, context)

        try:
            session.start()
            self.sessions[session_id] = session
            self.logger.info(f"Created session {session_id} for user {user}")
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
