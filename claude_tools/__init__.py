"""
HiveMatrix Tools for Claude Code

Python tools that expose HiveMatrix services to Claude Code.
These tools handle service-to-service communication and provide
a clean API for the AI assistant.

All tools communicate with internal HiveMatrix services only (Codex, KnowledgeTree, etc.)
and do NOT directly access external services (Datto RMM, Freshservice, etc.).
"""

from .codex_tools import (
    get_companies,
    get_company,
    get_tickets,
    get_ticket,
    update_ticket,
    get_company_contacts,
    get_company_locations,
    get_psa_agents
)

from .knowledge_tools import (
    search_knowledge,
    browse_knowledge,
    get_article
)

from .device_tools import (
    get_devices,
    get_device,
    get_company_assets,
    execute_command
)

__all__ = [
    # Codex tools - Company & PSA data
    'get_companies',
    'get_company',
    'get_company_contacts',
    'get_company_locations',
    'get_psa_agents',

    # Codex tools - Ticket management
    'get_tickets',
    'get_ticket',
    'update_ticket',

    # Knowledge tools - Documentation & KB
    'search_knowledge',
    'browse_knowledge',
    'get_article',

    # Device/Asset tools - RMM data (via Codex)
    'get_devices',
    'get_device',
    'get_company_assets',
    'execute_command',
]
