# Brain Hair Chat System - AI Tech Assistant

## Overview

The Brain Hair Chat System provides a conversational interface where MSP technicians can interact with Claude AI to help solve tickets, search documentation, manage devices, and execute commands with approval workflows.

## Features

### 🤖 AI-Powered Assistance
- Natural language understanding of tech support questions
- Context-aware responses based on current ticket/client
- Access to all HiveMatrix data (tickets, clients, devices, knowledge base)
- Intelligent suggestions and troubleshooting steps

### 🎫 Ticket Context Management
- Set current ticket number to focus conversation
- Automatically fetch ticket details
- Search related knowledge base articles
- View client devices associated with ticket

### 💻 Command Execution with Approval
- Claude can suggest PowerShell commands to run on client devices
- Approval workflow requires tech confirmation
- Shows command, target device, and reason before execution
- Full audit logging of all command approvals/denials
- Integrates with Datto RMM for remote execution

### 📊 Data Integration
All data is automatically PHI/CJIS filtered:
- **Codex**: Tickets, clients, company information
- **KnowledgeTree**: Documentation and procedures
- **Datto**: Device information and management
- **FreshService**: Ticket system integration

### 🔒 Security & Compliance
- All data filtered through Presidio for PHI/CJIS compliance
- Names shown as "FirstName L." format
- Email/phone/SSN automatically redacted
- Full audit trail of all actions
- User authentication required

## User Interface

### Main Chat Window
- **Clean, modern dark theme** optimized for readability
- **Real-time typing indicators** when Claude is thinking
- **Message history** preserved during session
- **Auto-scrolling** to latest messages

### Context Panel
Located in header, shows:
- Current ticket number
- Current client
- Logged-in user

### Sidebar Quick Actions
- 📋 Set Ticket Number
- 🏢 Set Client
- 🎫 List Recent Tickets
- 📚 Search Knowledge
- 💻 List Devices
- 🗑️ Clear Chat

### Command Approval UI
When Claude wants to run a command, a special approval card appears showing:
- Target device name
- Full PowerShell command
- Reason/purpose for the command
- **Approve** button (green)
- **Deny** button (red)

## API Endpoints

### Chat Interface
```
GET /chat
```
Renders the chat UI (requires authentication)

### Send Message
```
POST /api/chat
Content-Type: application/json

{
  "message": "user message",
  "ticket": "12345" or null,
  "client": "Acme Corp" or null,
  "history": [
    {"role": "user", "content": "previous message"},
    {"role": "assistant", "content": "previous response"}
  ]
}
```

Response:
```json
{
  "response": "Claude's response message",
  "command_request": {  // Optional
    "id": "uuid",
    "device": "WORKSTATION-001",
    "command": "Get-ComputerInfo | Select-Object ...",
    "reason": "Check system information for troubleshooting"
  }
}
```

### Approve Command
```
POST /api/chat/command/approve
Content-Type: application/json

{
  "command_id": "uuid"
}
```

Response:
```json
{
  "status": "success",
  "output": "Command output here..."
}
```

### Deny Command
```
POST /api/chat/command/deny
Content-Type: application/json

{
  "command_id": "uuid"
}
```

## Example Conversations

### Example 1: Ticket Troubleshooting
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

### Example 2: Knowledge Base Search
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

### Example 3: Client Device Management
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

## Integration Points

### Current
- ✅ Codex (companies, basic data)
- ✅ PHI/CJIS filtering via Presidio
- ✅ User authentication
- ✅ Command approval workflow
- ✅ Audit logging

### Pending Implementation
- ⏳ KnowledgeTree full browsing
- ⏳ Codex tickets API
- ⏳ Datto RMM command execution
- ⏳ FreshService ticket integration
- ⏳ Real Claude API integration (currently simulated)
- ⏳ Database-backed chat sessions
- ⏳ Command history persistence

## Technical Architecture

### Frontend (`chat.html`)
- Vanilla JavaScript (no framework dependencies)
- Responsive design
- Real-time updates
- Auto-scrolling and textarea resizing
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)

### Backend (`chat_routes.py`)
- Flask routes for chat and command management
- Session management (in-memory, upgradeable to Redis/DB)
- Command approval queue
- Integration with all HiveMatrix services
- Logging via Helm logger

### Security
- JWT token authentication on all routes
- PHI/CJIS filtering on all data
- Command audit trail
- User permission checks

## Future Enhancements

1. **Real Claude API Integration**
   - Replace simulated responses with actual Claude API calls
   - Advanced context management
   - Multi-turn conversation understanding

2. **Datto RMM Integration**
   - Real remote PowerShell execution
   - Command output streaming
   - Script library management

3. **Advanced Features**
   - Voice input/output
   - Screen sharing for guided troubleshooting
   - Automated ticket updates
   - Suggested solutions based on ticket history
   - Integration with more tools (ConnectWise, etc.)

4. **Analytics**
   - Common issues detected
   - Resolution time tracking
   - Claude assistance effectiveness metrics

## Usage Tips

1. **Set Context Early**: Use "Set Ticket" and "Set Client" to give Claude context
2. **Be Specific**: Claude responds better to specific questions
3. **Review Commands**: Always review commands before approving
4. **Use Quick Actions**: Sidebar shortcuts for common tasks
5. **Keep History**: Don't clear chat mid-troubleshooting for better context

## Access

Navigate to: `https://your-server/brainhair/chat`

Or from Brain Hair home page, click "Open Chat Interface"

## Support

For issues or feature requests, contact the HiveMatrix development team or check the main ARCHITECTURE.md document.
