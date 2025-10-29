# HiveMatrix Brainhair

**The AI Technical Support Assistant for HiveMatrix**

Brainhair is HiveMatrix's AI-powered technical support assistant that helps MSP technicians troubleshoot issues, manage tickets, search documentation, update billing information, and interact with organizational data through natural language conversations powered by Claude AI.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [AI Tools](#ai-tools)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Security & Compliance](#security--compliance)
- [Integration Status](#integration-status)
- [Known Issues](#known-issues)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Overview

Brainhair provides:
- **AI-Powered Assistance**: Natural language interface to all HiveMatrix data
- **Ticket Management**: View, search, and analyze support tickets from Codex
- **Device Management**: Check device status, health, and manage devices
- **Knowledge Base**: Search, create, update, and organize documentation
- **Billing Management**: View and update client billing plans, features, and pricing
- **Network Equipment**: Manage switches, firewalls, and network devices
- **Chat History**: Searchable conversation history with context preservation
- **PHI/CJIS Compliance**: Automatic data anonymization for sensitive information
- **Command Approval**: Human-in-the-loop workflow for potentially destructive operations

**Port:** 5050 (standard)

### What Brainhair Does

Brainhair integrates Claude AI with the HiveMatrix ecosystem to provide:

1. **Data Access** - Natural language queries across all Codex data (tickets, companies, assets, contacts)
2. **Knowledge Management** - Search and maintain organizational documentation in KnowledgeTree
3. **Billing Operations** - View and update client billing plans, features, and pricing structures
4. **Technical Support** - Assist technicians with troubleshooting using AI analysis
5. **Audit Trail** - Complete logging of all AI actions and decisions
6. **Compliance** - Automatic PHI/CJIS filtering for regulated environments

---

## Features

### 🤖 AI Integration
- **Claude Code Engine**: Uses Claude Code as the AI backend with full tool access
- **Server-Sent Events (SSE)**: Real-time streaming of AI responses
- **Tool Execution**: Python tools for data access and modification
- **Session Management**: Independent context per chat session
- **No API Keys Required**: Uses local Claude Code installation

### 🎫 Ticket Management
- View and search support tickets from Codex
- Filter by status, priority, company
- Analyze ticket patterns and trends
- Link tickets to chat sessions

### 💼 Billing Management
- View client billing plans and features
- Update billing information
- Set company-specific pricing
- Manage feature assignments
- Import billing plan configurations

### 💻 Device & Network Management
- Check device status and health from Datto RMM
- View device inventory and details
- Manage network equipment (switches, firewalls, APs)
- Track device assignments to companies

### 📚 Knowledge Base Integration
- Search documentation from KnowledgeTree
- Create and update knowledge articles
- Organize knowledge by categories
- Full-text search capabilities

### 🔒 Security & Compliance
- **PHI/CJIS Filtering**: Automatic data anonymization using Microsoft Presidio
- **Command Approval**: Human-in-the-loop for destructive operations
- **JWT Authentication**: Token-based access control
- **Audit Logging**: Complete trail of all actions

### 📝 Chat Features
- **Persistent History**: PostgreSQL-backed chat storage
- **Session Context**: Link chats to tickets and clients
- **Search History**: Find past conversations
- **Session Resume**: Continue previous conversations
- **Auto-Titles**: AI-generated chat titles

---

## Architecture

Brainhair uses **Claude Code as its AI engine**, spawning a Claude Code process for each chat session.

```
┌────────────────────────────────────────────┐
│  User Interface (Chat UI)                  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  Brainhair Backend (Flask/SSE)             │
│  ┌──────────────┐  ┌───────────────────┐  │
│  │  Session     │  │  PHI/CJIS         │  │
│  │  Manager     │  │  Filter           │  │
│  └──────────────┘  └───────────────────┘  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  Claude Code Process (per session)         │
│  ┌──────────────┐  ┌───────────────────┐  │
│  │  AI Tools    │  │  System Prompt    │  │
│  │  (Python)    │  │  (Instructions)   │  │
│  └──────────────┘  └───────────────────┘  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│  HiveMatrix Services                       │
│  Codex | KnowledgeTree | Ledger | Datto   │
└────────────────────────────────────────────┘
```

### Key Components

**1. Session Manager** (`app/claude_session_manager.py`)
- Spawns one Claude Code process per chat session
- Streams responses via Server-Sent Events (SSE)
- Intercepts tool calls that need approval
- Applies PHI/CJIS filtering to all responses
- Handles bash tool execution and output streaming
- Manages session lifecycle and cleanup

**2. Python AI Tools** (`ai_tools/`)
- **Tickets**: `list_tickets.py` - List and retrieve ticket information
- **Companies**: `list_companies.py` - Company data access
- **Devices**: `list_devices.py` - Device inventory and health
- **Knowledge**: `search_knowledge.py`, `manage_knowledge.py`, `update_knowledge.py`
- **Billing**: `get_billing.py`, `update_billing.py`, `set_company_plan.py`, `update_features.py`, `import_billing_plans.py`
- **Network**: `manage_network_equipment.py` - Network device management
- **Utilities**: `set_chat_title.py`, `approval_helper.py`

**3. System Prompt** (`claude_tools/SYSTEM_PROMPT.md`)
- Comprehensive AI assistant instructions
- Tool documentation and usage guidelines
- Troubleshooting workflows
- Security and safety rules

**4. Database** (PostgreSQL)
- `chat_sessions` - Chat session metadata with context
- `chat_messages` - Individual messages with tool tracking

---

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Claude Code installed and accessible in PATH
- HiveMatrix Core service running (for authentication)
- HiveMatrix Codex service running (for data access)

### Quick Install via Helm

Brain Hair can be installed via Helm's auto-installation system:

```bash
cd hivematrix-helm
source pyenv/bin/activate
python install_manager.py install brainhair
```

### Manual Installation

```bash
cd hivematrix-brainhair
./install.sh
```

This will:
- Create Python virtual environment
- Install dependencies from `requirements.txt`
- Prompt for database configuration
- Initialize database tables

### Database Setup

**1. Create PostgreSQL database and user:**

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

**2. Run database initialization:**

```bash
cd hivematrix-brainhair
source pyenv/bin/activate
python init_db.py
```

When prompted, enter:
- **Host:** `localhost` (press Enter)
- **Port:** `5432` (press Enter)
- **Database Name:** `brainhair_db` (press Enter)
- **User:** `brainhair_user` (press Enter)
- **Password:** (your password from step 1)

The script will:
1. Test the database connection
2. Save configuration to `instance/brainhair.conf`
3. Create all required tables (chat_sessions, chat_messages)

### Claude Code Setup

Ensure Claude Code is installed and accessible:

```bash
# Check if Claude Code is available
which claude

# If not installed, follow Claude Code installation instructions
```

The session manager will look for the `claude` binary in your PATH.

---

## Configuration

### Environment Variables

File: `.flaskenv` (auto-generated by Helm)

```bash
FLASK_APP=run.py
FLASK_ENV=development
SERVICE_NAME=brainhair
CORE_SERVICE_URL=http://localhost:5000
HELM_SERVICE_URL=http://localhost:5004
```

### Database Configuration

File: `instance/brainhair.conf` (created by `init_db.py`)

```ini
[database]
connection_string = postgresql://brainhair_user:password@localhost:5432/brainhair_db

[database_credentials]
db_host = localhost
db_port = 5432
db_user = brainhair_user
db_dbname = brainhair_db
```

**Note**: The database password is stored securely in `instance/brainhair.conf` which is excluded from git via `.gitignore`.

### Service Discovery

File: `services.json` (auto-generated by Helm)

```json
{
  "codex": {
    "url": "http://localhost:5010",
    "port": 5010
  },
  "knowledgetree": {
    "url": "http://localhost:5020",
    "port": 5020
  }
}
```

---

## Usage

### Starting Brainhair

**Via Helm (Recommended):**
```bash
cd hivematrix-helm
./start.sh
```

**Manually:**
```bash
cd hivematrix-brainhair
source pyenv/bin/activate
python run.py
```

The service runs on port 5050 (localhost only) and is accessed via Nexus at:
```
https://your-domain/brainhair/chat
```

### Chat Interface

Navigate to `/brainhair/chat` and interact with the AI.

**Example Conversations:**

#### Example 1: Ticket Troubleshooting
```
Tech: I'm working on ticket #12345, user can't access VPN

Claude: I've pulled up ticket #12345. Let me search the knowledge base
        for VPN troubleshooting steps.

        Based on our documentation, here are the common VPN issues:
        1. Check Windows Firewall settings
        2. Verify VPN client version
        3. Test network connectivity

        Would you like me to run a diagnostic command on the user's
        device to check their VPN client status?

Tech: Yes, run the diagnostic

Claude: [Command Approval Request]
        Device: WORK-USER-PC
        Command: Get-VpnConnection | Select-Object Name, ConnectionStatus, ServerAddress
        Purpose: Check VPN connection configuration and status

        [Approve] [Deny]

Tech: [Clicks Approve]

Claude: Command executed successfully. Results show:
        - VPN connection "Corporate VPN" exists
        - Status: Disconnected
        - Server: vpn.company.com

        The connection is configured correctly. Let's check if the
        firewall is blocking it...
```

#### Example 2: Knowledge Base Search
```
Tech: How do I reset a user's password in Active Directory?

Claude: I'll search the knowledge base for AD password reset procedures.

        Found: "Active Directory Password Reset - Standard Procedure"

        Steps:
        1. Open Active Directory Users and Computers
        2. Navigate to the user's OU
        3. Right-click user → Reset Password
        4. Check "User must change password at next logon"
        5. Click OK

        Alternative: I can provide the PowerShell command if you prefer
        to do this remotely. Would you like me to do that?
```

#### Example 3: Client Device Management
```
Tech: Set client to Acme Corp

Claude: Now viewing client: Acme Corp

        I can help with:
        - List all devices for Acme Corp
        - Check device health/status
        - Run diagnostics
        - View installed software

        What would you like to know about Acme Corp's devices?

Tech: List their devices

Claude: Acme Corp has 47 devices:

        Workstations (42):
        - 38 Windows 10/11
        - 4 macOS

        Servers (5):
        - DC01 (Domain Controller)
        - FILE01 (File Server)
        - SQL01 (Database Server)
        - WEB01 (Web Server)
        - BACKUP01 (Backup Server)

        Would you like details on any specific device?
```

### Chat History

Access past conversations at `/brainhair/history`:
- Search all conversations
- Filter by ticket or client
- Resume previous sessions
- View conversation summaries

---

## AI Tools

### Data Retrieval Tools (Pre-Approved)

These tools require no approval and are safe for AI to use:

#### Ticket Management
```bash
# List recent tickets
python ai_tools/list_tickets.py list [codex_url] [filter_type]

# Get specific ticket
python ai_tools/list_tickets.py get [ticket_id] [codex_url] [filter_type]
```

#### Company Information
```bash
# List companies
python ai_tools/list_companies.py [limit] [codex_url] [filter_type]
```

#### Device Management
```bash
# List devices for a company
python ai_tools/list_devices.py [company_account] [codex_url] [filter_type]
```

#### Knowledge Base
```bash
# Search knowledge base
python ai_tools/search_knowledge.py search [query] [filter_type]

# Browse knowledge tree
python ai_tools/search_knowledge.py browse [path] [filter_type]
```

### Data Modification Tools (Pre-Approved with Caution)

#### Billing Management
```bash
# Get billing information
python ai_tools/get_billing.py [account_number]

# Update billing
python ai_tools/update_billing.py [account_number] [field] [value]

# Set company plan
python ai_tools/set_company_plan.py [account_number] [plan_name] [term]

# Update features
python ai_tools/update_features.py [account_number] [feature] [value]
```

#### Knowledge Management
```bash
# Manage knowledge articles
python ai_tools/manage_knowledge.py [action] [args...]

# Update knowledge content
python ai_tools/update_knowledge.py [node_id] [content]
```

#### Network Equipment
```bash
# Manage network devices
python ai_tools/manage_network_equipment.py [action] [args...]
```

### Python API Usage

You can import AI tools and use them programmatically:

```python
from brainhair_auth import get_auth

# Authenticate
auth = get_auth()

# Make API calls
response = auth.get("/api/health")
print(response.json())

# Search knowledge
response = auth.get("/api/knowledge/search", params={"q": "VPN", "filter": "phi"})
results = response.json()

# List companies
response = auth.get("/api/codex/companies", params={"filter": "phi"})
companies = response.json()
```

**Environment Variables for AI Tools:**

Optional environment variables for customizing AI tool behavior:
- `BRAINHAIR_URL`: Base URL for Brainhair service
- `BRAINHAIR_USERNAME`: Username for authentication
- `BRAINHAIR_PASSWORD`: Password for authentication

### Approval-Required Tools

Remote PowerShell commands on devices (via Datto RMM) require human approval:

```
You: Check disk space on SERVER-01
AI: I'd like to run this command:
    Device: SERVER-01
    Command: Get-PSDrive C | Select-Object Used,Free
    Reason: Ticket #17635 - Check disk space

    [Approve] [Deny]
```

---

## Database Schema

Brainhair uses **PostgreSQL** for chat history storage.

### Tables

#### chat_sessions
**Purpose:** Store chat session metadata and context

**Columns:**
- `id` (String, Primary Key) - UUID for session
- `user_id` (String, Indexed) - Keycloak user ID
- `user_name` (String) - Display name
- `ticket_number` (String, Indexed) - Associated ticket number
- `client_name` (String, Indexed) - Associated client name
- `created_at` (DateTime, Indexed) - Session start time
- `updated_at` (DateTime) - Last message time
- `ended_at` (DateTime) - Session end time
- `is_active` (Boolean, Indexed) - Active session flag
- `title` (String) - AI-generated or manual title
- `summary` (Text) - Conversation summary

**Features:**
- Each session linked to a user
- Optional context (ticket, client) for better organization
- Auto-generated titles and summaries
- Searchable by user, ticket, client, or date

#### chat_messages
**Purpose:** Store individual messages in conversations

**Columns:**
- `id` (Integer, Primary Key) - Auto-incrementing message ID
- `session_id` (String, Foreign Key, Indexed) - References chat_sessions.id
- `role` (String) - "user" or "assistant"
- `content` (Text) - Message text
- `tool_calls` (JSON) - List of tools called in this message
- `tool_results` (JSON) - Results from tool calls
- `created_at` (DateTime, Indexed) - Message timestamp
- `was_filtered` (Boolean) - Whether PHI/CJIS filtering was applied
- `filter_type` (String) - "phi" or "cjis"

**Features:**
- Complete message history with timestamps
- Tool usage tracking for audit
- Filtering metadata for compliance
- Ordered by creation time

---

## API Endpoints

All API endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

### Chat

```bash
# Start new chat session
POST /api/chat
{
  "message": "Show me recent tickets",
  "ticket_number": "17635",  # optional
  "client_name": "ACME Corp"  # optional
}

# Stream chat response (SSE)
GET /api/chat/stream?session_id={session_id}&message={message}

# Get session messages
GET /api/sessions/{session_id}

# List user's sessions
GET /api/sessions?limit=50

# Search chat history
GET /api/sessions/search?q={query}
```

### Command Approval

```bash
# Submit command for approval
POST /api/command/approve
{
  "session_id": "abc-123",
  "command": "Get-PSDrive C",
  "device": "SERVER-01",
  "reason": "Check disk space"
}

# Get pending approvals
GET /api/command/pending
```

### Health Check

```bash
GET /health
```

---

## Security & Compliance

### PHI/CJIS Filtering

All data is automatically filtered using Microsoft Presidio before being shown to users:

**Redacted Entities:**
- **Names** → "FirstName L." format
- **Emails** → Fully redacted
- **Phone Numbers** → Fully redacted
- **SSNs** → Fully redacted
- **IP Addresses** → Partially masked
- **MAC Addresses** → Partially masked
- **Credit Cards** → Fully redacted

**Filter Types:**
- `phi` - HIPAA compliance (healthcare data)
- `cjis` - Criminal Justice Information Services compliance

### Authentication

- **JWT Tokens**: Required for all routes via `@token_required` decorator
- **Service Tokens**: Used by AI tools to call other HiveMatrix services
- **User Context**: All actions logged with user ID and timestamp

### Command Safety

- **Read-Only Tools**: Pre-approved (list_tickets, search_knowledge, etc.)
- **Data Modification**: Pre-approved but logged (update_billing, set_company_plan)
- **Remote Commands**: Require human approval (PowerShell on devices)
- **Audit Trail**: Complete logging of all tool calls and results

### Best Practices

1. Enable PHI/CJIS filtering for all sessions
2. Review approval requests carefully before approving
3. Regularly audit tool usage logs
4. Keep Claude Code updated
5. Use strong database passwords
6. Restrict access to sensitive AI tools
7. Monitor for unusual AI behavior

---

## Integration Status

### What's Working ✅

- **Claude Code Integration**: 100% functional with streaming responses
- **Codex Integration**: Companies, tickets, and contacts APIs working
- **Datto Integration**: Device data and inventory working
- **PHI/CJIS Filtering**: Automatic data anonymization operational
- **Command Approval**: Human-in-the-loop workflow for remote commands
- **Chat History**: PostgreSQL-backed session persistence
- **Authentication**: JWT token-based access control

### In Progress 🟡

- **KnowledgeTree Integration**: API endpoints need debugging (500 errors)
- **Datto RMM Execution**: Command approval works, real execution pending
- **Billing Tools**: All tools created, testing in progress

### Planned 📋

- **FreshService Integration**: Real-time ticket sync via webhooks
- **Advanced AI Features**: Multi-turn context, auto-ticket updates
- **Voice Integration**: Voice input/output for hands-free operation
- **Analytics Dashboard**: AI effectiveness metrics and insights

---

## Known Issues

1. **KnowledgeTree 500 Errors**
   - Service-to-service communication needs debugging
   - Search and browse endpoints returning errors
   - Workaround: Direct KnowledgeTree access

2. **Session Timeout**
   - Claude Code processes may timeout on long-running tasks
   - Workaround: Break complex tasks into smaller steps

3. **Filter Performance**
   - PHI/CJIS filtering adds ~100-200ms latency per response
   - Acceptable for most use cases

---

## Troubleshooting

### Streaming Stops After Tool Use

**Symptom**: AI response stops when trying to run bash commands

**Check**: Look for `[STREAM] Process wait timed out` in logs

**Solution**: Ensure you have the latest code with the tool_use streaming fix (2025-10-22)

### Claude Code Not Found

**Symptom**: `FileNotFoundError: claude binary not found`

**Solution**:
1. Verify Claude Code is installed: `which claude`
2. Update the claude_bin path in `claude_session_manager.py` if needed
3. Ensure Claude Code is in your PATH

### No Response from AI

**Symptom**: Chat sends message but nothing comes back

**Check**:
1. View logs: `cd ../hivematrix-helm && python logs_cli.py brainhair --tail 50`
2. Check Claude Code is accessible: `which claude`
3. Test streaming: `cd hivematrix-brainhair && python test_claude_streaming.py`
4. Verify Core service is running (authentication)

### Database Connection Errors

**Symptom**: "Connection refused" or "database does not exist"

**Solution**:
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify database exists: `psql -h localhost -U brainhair_user -d brainhair_db`
3. Re-run `init_db.py` if configuration is wrong

### PHI/CJIS Filter Not Working

**Symptom**: Sensitive data appears unredacted

**Check**:
1. Verify filter_type is set ('phi' or 'cjis')
2. Check Presidio is installed: `pip list | grep presidio`
3. Review filter logs in Helm logs

### Session Not Resuming

**Symptom**: Chat history doesn't load when clicking on a past conversation

**Check**:
1. Verify session ID is valid
2. Check database for session: `SELECT * FROM chat_sessions WHERE id='session_id'`
3. Ensure messages exist: `SELECT COUNT(*) FROM chat_messages WHERE session_id='session_id'`

---

## Development

### Project Structure

```
hivematrix-brainhair/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── routes.py                # Web routes and API endpoints
│   ├── auth.py                  # @token_required decorator
│   ├── claude_session_manager.py # Claude Code session management
│   ├── data_filter.py           # PHI/CJIS filtering with Presidio
│   └── templates/               # HTML templates (BEM styled)
├── ai_tools/                    # Python tools for AI
│   ├── list_tickets.py          # Ticket management
│   ├── list_companies.py        # Company data
│   ├── list_devices.py          # Device inventory
│   ├── search_knowledge.py      # Knowledge search
│   ├── manage_knowledge.py      # Knowledge CRUD
│   ├── get_billing.py           # Billing data
│   ├── update_billing.py        # Billing updates
│   ├── set_company_plan.py      # Plan management
│   ├── update_features.py       # Feature management
│   ├── manage_network_equipment.py # Network devices
│   └── brainhair_auth.py        # Authentication helper
├── claude_tools/
│   └── SYSTEM_PROMPT.md         # AI instructions
├── models.py                    # Database models
├── extensions.py                # Flask extensions
├── init_db.py                   # Database setup script
├── run.py                       # Application entry point
├── install.sh                   # Installation script
└── requirements.txt             # Python dependencies
```

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

### Testing AI Tools Directly

Test the Python tools independently:

```bash
cd hivematrix-brainhair
source pyenv/bin/activate

# List tickets
python ai_tools/list_tickets.py list http://localhost:5010 phi

# Get specific ticket
python ai_tools/list_tickets.py get 17635 http://localhost:5010 phi

# Search knowledge
python ai_tools/search_knowledge.py search "password reset" phi

# Get billing info
python ai_tools/get_billing.py 100123
```

### Adding New AI Tools

1. **Create Python script** in `ai_tools/`:
```python
#!/usr/bin/env python3
"""
Tool description here
"""
import sys
from brainhair_auth import get_service_token

def main():
    # Your tool logic here
    pass

if __name__ == "__main__":
    main()
```

2. **Document in SYSTEM_PROMPT.md**: Add tool description and usage

3. **Test with Claude Code**: Verify the AI can call your tool correctly

4. **Add authentication**: Use `brainhair_auth.py` for service-to-service calls

### Running Tests

```bash
# Test Claude Code integration
python test_claude_simple.py

# Test streaming
python test_claude_streaming.py

# Test tool execution
python test_claude_tools.py

# Test billing tools
python test_billing_tools.py
```

---

## Related Modules

- **HiveMatrix Core** (Port 5000): Authentication and identity management
- **HiveMatrix Codex** (Port 5010): Data platform - source of tickets, companies, assets
- **HiveMatrix KnowledgeTree** (Port 5020): Documentation and knowledge base
- **HiveMatrix Ledger** (Port 5030): Billing calculations
- **HiveMatrix Helm** (Port 5004): Service manager with centralized logging
- **HiveMatrix Nexus** (Port 443): UI gateway with SSL

---

## Documentation

- `CHAT_SYSTEM.md` - Complete chat system documentation
- `TODO.md` - Project status and roadmap
- `claude_tools/SYSTEM_PROMPT.md` - AI instructions and tool docs
- `../hivematrix-helm/ARCHITECTURE.md` - Overall HiveMatrix architecture

---

## License

See main HiveMatrix LICENSE file

---

## Contributing

When adding features to Brainhair:
1. Follow the HiveMatrix architecture patterns
2. Use `@token_required` for all protected routes
3. Use BEM classes for all HTML (no CSS in this service)
4. Document new AI tools in SYSTEM_PROMPT.md
5. Test tools both directly and via AI
6. Add PHI/CJIS filtering for sensitive data
7. Consider approval requirements for destructive operations

For questions, refer to `ARCHITECTURE.md` in the main HiveMatrix repository.

---

**Version**: 2.1.0
**Status**: Production Ready
**Last Updated**: 2025-10-28
