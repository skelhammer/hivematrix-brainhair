# Brain Hair - AI Technical Support Assistant

Brain Hair is HiveMatrix's AI-powered technical support assistant that helps MSP technicians troubleshoot issues, search documentation, manage tickets, and execute remote commands with approval workflows.

## Features

- 🤖 **Claude Code Integration**: Uses Claude Code as the AI backend with full tool access
- 🎫 **Ticket Management**: View, search, and update support tickets from Codex
- 💻 **Device Management**: Check device status, health, and execute remote commands
- 📚 **Knowledge Base**: Search and browse documentation from KnowledgeTree
- 🔒 **PHI/CJIS Filtering**: Automatic data anonymization for compliance
- ✅ **Command Approval**: Human-in-the-loop workflow for PowerShell commands
- 🌊 **Real-Time Streaming**: Server-Sent Events (SSE) for live AI responses
- 📝 **Comprehensive Logging**: Full audit trail of all actions

## Quick Start

### Installation

Brain Hair can be installed via Helm's auto-installation system:

```bash
cd hivematrix-helm
source pyenv/bin/activate
python install_manager.py install brainhair
```

Or manually:

```bash
cd hivematrix-brainhair
./install.sh
```

### Database Setup

Brain Hair requires PostgreSQL for storing chat history. Set up the database before first run:

**1. Create the database and user in PostgreSQL:**

```bash
sudo -u postgres psql
```

```sql
-- Create database
CREATE DATABASE brainhair_db;

-- Create user
CREATE USER brainhair_user WITH PASSWORD 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE brainhair_db TO brainhair_user;

-- Connect to the database
\c brainhair_db

-- Grant schema permissions (required for PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO brainhair_user;
GRANT USAGE, CREATE ON SCHEMA public TO brainhair_user;

-- Exit psql
\q
```

**2. Run the initialization script:**

```bash
cd hivematrix-brainhair
source pyenv/bin/activate
python init_db.py
```

The script will:
- Prompt for database connection details (host, port, database name, user, password)
- Test the connection
- Save configuration to `instance/brainhair.conf`
- Create database tables (chat_sessions, chat_messages)

**Note**: The database password is stored securely in `instance/brainhair.conf` which is excluded from git via `.gitignore`.

### Running

Start via Helm:
```bash
cd hivematrix-helm
./start.sh
```

Or manually:
```bash
cd hivematrix-brainhair
source pyenv/bin/activate
python run.py
```

The service runs on port 5050 (localhost only) and is accessed via Nexus at:
```
https://your-server/brainhair/chat
```

## Architecture

Brain Hair uses **Claude Code as its AI engine**, spawning a Claude Code process for each chat session. This provides:

- Full Claude Code capabilities (all tools, MCP support, code execution)
- No API key required (uses server-side Claude Code installation)
- Automatic PHI/CJIS filtering on all responses
- Command approval workflow for safety
- Session isolation with independent context

### How It Works

```
User → Chat UI → Brain Hair Backend → Claude Code Process → HiveMatrix Services
                       ↓                      ↓
                  Session Manager      Python Tools
                       ↓                      ↓
                  PHI/CJIS Filter       (ai_tools/*.py)
```

### Components

**1. Session Manager** (`app/claude_session_manager.py`)
- Spawns one Claude Code process per chat session
- Streams responses via Server-Sent Events (SSE)
- Intercepts tool calls that need approval
- Applies PHI/CJIS filtering to all responses
- Handles bash tool execution and output streaming

**2. Python Tools** (`ai_tools/`)
- `list_tickets.py` - Ticket management (list, get details)
- `list_companies.py` - Company information
- `list_devices.py` - Device status and health
- `search_knowledge.py` - Knowledge base search

**3. System Prompt** (`claude_tools/SYSTEM_PROMPT.md`)
- Comprehensive AI assistant instructions
- Tool documentation and usage guidelines
- Troubleshooting workflows
- Security and safety rules

## Recent Fixes

### Bash Command Streaming (2025-10-22)

**Problem**: When Claude Code executed bash commands (Python tools), the streaming would stop after the tool_use request, causing the process to hang and timeout.

**Root Cause**: The session manager was breaking the read loop on `message_stop`, but when `stop_reason` is `tool_use`, the process continues running to execute the bash command. This left the process hanging until the 10-second timeout killed it.

**Solution**:
- Track `stop_reason` from `message_delta` events
- When `message_stop` has `stop_reason == "tool_use"`, continue reading instead of breaking
- This allows capturing the bash command output and completion events
- Added comprehensive `[STREAM]` logging for debugging

**Files Changed**:
- `app/claude_session_manager.py` - Fixed streaming logic and added extensive logging
- `hivematrix-nexus/app/routes.py` - Added SSE streaming support to prevent buffering

## Usage

### Chat Interface

Navigate to `/brainhair/chat` and interact with the AI:

```
You: Look up ticket 17635
AI: [runs python ai_tools/list_tickets.py get 17635 codex phi]
    Here's ticket #17635:
    Subject: VPN connection issues
    Status: Open
    Priority: High
    ...
```

### Available Commands

The AI can execute these **without approval** (data retrieval only):
- List tickets: `"Show me recent tickets"`
- List companies: `"List all companies"`
- Search knowledge: `"How do I reset a password?"`
- List devices: `"Show devices for ACME Corp"`

### Command Approval Workflow

For remote PowerShell commands on devices (via Datto RMM), the AI will request approval:

```
You: Check disk space on SERVER-01
AI: I'd like to run this command:
    Device: SERVER-01
    Command: Get-PSDrive C | Select-Object Used,Free
    Reason: Ticket #17635 - Check disk space

    [Approve] [Deny]
```

## Configuration

Brain Hair is configured via Helm's central configuration system:

**`.flaskenv`** (auto-generated by Helm):
```bash
FLASK_APP=run.py
FLASK_ENV=development
SERVICE_NAME=brainhair
CORE_SERVICE_URL=http://localhost:5000
HELM_SERVICE_URL=http://localhost:5004
```

**`instance/brainhair.conf`** (auto-generated by Helm):
```ini
[database]
connection_string = postgresql://brainhair_user:password@localhost:5432/brainhair_db
```

## Development

### Debugging Streaming Issues

View real-time logs with `[STREAM]` markers:

```bash
cd hivematrix-helm
source pyenv/bin/activate
python logs_cli.py brainhair --tail 100 | grep STREAM
```

This shows:
- Every line received from Claude Code
- JSON parsing status
- Event types and handling
- Tool use detection
- Process termination details

### Testing Tool Execution

Test the Python tools directly:

```bash
cd hivematrix-brainhair
source pyenv/bin/activate

# List tickets
python ai_tools/list_tickets.py list codex phi

# Get specific ticket
python ai_tools/list_tickets.py get 17635 codex phi

# List companies
python ai_tools/list_companies.py 10

# Search knowledge
python ai_tools/search_knowledge.py search "password reset" phi
```

### Adding New Tools

1. Create a new Python script in `ai_tools/`
2. Use `brainhair_auth.py` for authentication
3. Document it in `claude_tools/SYSTEM_PROMPT.md`
4. Test with Claude Code

## Security & Compliance

### PHI/CJIS Filtering

All data is automatically filtered using Microsoft Presidio:
- Names → "FirstName L." format
- Emails → Redacted
- Phone numbers → Redacted
- SSNs → Redacted
- IP addresses → Masked
- MAC addresses → Masked

### Authentication

- JWT token required for all routes
- Service-to-service tokens for tool access
- Full audit logging of all actions

### Command Safety

- Read-only Python tools are pre-approved
- Remote PowerShell commands require human approval
- All commands logged with user, timestamp, and justification

## Troubleshooting

### Streaming Stops After Tool Use

**Symptom**: AI response stops when trying to run bash commands

**Check**: Look for `[STREAM] Process wait timed out` in logs

**Solution**: Ensure you have the latest code with the tool_use streaming fix

### Claude Code Not Found

**Symptom**: `FileNotFoundError: claude binary not found`

**Solution**: Update the claude_bin path in `claude_session_manager.py` line 101

### No Response from AI

**Symptom**: Chat sends message but nothing comes back

**Check**:
1. View logs: `python logs_cli.py brainhair --tail 50`
2. Check Claude Code is accessible: `which claude`
3. Test streaming: `cd hivematrix-brainhair && python test_claude_streaming.py`

## Documentation

- `CHAT_SYSTEM.md` - Complete chat system documentation
- `TODO.md` - Project status and roadmap
- `claude_tools/SYSTEM_PROMPT.md` - AI instructions and tool docs
- `../hivematrix-helm/ARCHITECTURE.md` - Overall HiveMatrix architecture

## Support

For issues or feature requests:
- Check the logs: `python logs_cli.py brainhair`
- Review TODO.md for known issues
- Consult ARCHITECTURE.md for system design

---

**Version**: 2.0.1
**Status**: Production Ready
**Last Updated**: 2025-10-22
