"""
HiveMatrix Tools for Claude Code

Python tools that expose HiveMatrix services to Claude Code.
These tools handle service-to-service communication and provide
a clean API for the AI assistant.
"""

from .codex_tools import (
    get_companies,
    get_company,
    get_tickets,
    get_ticket,
    update_ticket
)

from .knowledge_tools import (
    search_knowledge,
    browse_knowledge,
    get_article
)

from .datto_tools import (
    get_devices,
    get_device,
    execute_command
)

__all__ = [
    # Codex tools
    'get_companies',
    'get_company',
    'get_tickets',
    'get_ticket',
    'update_ticket',

    # Knowledge tools
    'search_knowledge',
    'browse_knowledge',
    'get_article',

    # Datto tools
    'get_devices',
    'get_device',
    'execute_command',
]
