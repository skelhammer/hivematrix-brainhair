# HiveMatrix BrainHair

AI-powered chat interface for natural language interaction with HiveMatrix.

## Overview

BrainHair provides a conversational interface to HiveMatrix, allowing users to query data, update billing, manage companies, and perform actions through natural language.

**Port:** 5050

## Features

- **Natural Language Queries** - Ask questions about companies, billing, tickets
- **Tool Calling** - AI executes actions via structured tool calls
- **Approval Workflow** - User confirmation for sensitive operations
- **Context Awareness** - Maintains conversation history
- **Streaming Responses** - Real-time AI response streaming

## Tech Stack

- Flask + Gunicorn
- Anthropic Claude API
- Server-Sent Events (SSE)

## AI Tools

Located in `ai_tools/`:
- `get_billing.py` - Query billing information
- `update_billing.py` - Modify billing rates
- `set_company_plan.py` - Change company plans
- `list_companies.py` - List companies
- `list_tickets.py` - Query tickets
- `search_knowledge.py` - Search knowledge base
- `manage_network_equipment.py` - Manage network devices

## Key Endpoints

- `GET /` - Chat interface
- `POST /api/chat` - Send message (SSE response)
- `GET /api/chats` - List chat sessions
- `DELETE /api/chats/<id>` - Delete chat session

## Environment Variables

- `ANTHROPIC_API_KEY` - Claude API key
- `CORE_SERVICE_URL` - Core service URL
- `CODEX_SERVICE_URL` - Codex service URL
- `LEDGER_SERVICE_URL` - Ledger service URL

## Documentation

For complete installation, configuration, and architecture documentation:

**[HiveMatrix Documentation](https://skelhammer.github.io/hivematrix-docs/)**

## License

MIT License - See LICENSE file
