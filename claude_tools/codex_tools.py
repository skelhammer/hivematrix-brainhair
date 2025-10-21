"""
Codex Service Tools

Tools for interacting with the Codex service (companies, tickets, clients).
"""

import os
import sys
import json

# Add parent directory to path to import service_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.service_client import call_service


def get_companies(limit: int = 100) -> dict:
    """
    Get list of all companies from Codex.

    Args:
        limit: Maximum number of companies to return

    Returns:
        {
            "companies": [
                {"id": 1, "name": "Company Name", "status": "active", ...},
                ...
            ],
            "count": 123
        }

    Example:
        >>> companies = get_companies(limit=50)
        >>> print(f"Found {companies['count']} companies")
    """
    try:
        response = call_service('codex', f'/api/companies?limit={limit}')
        return response.json()
    except Exception as e:
        return {
            'error': str(e),
            'companies': [],
            'count': 0
        }


def get_company(company_id: int) -> dict:
    """
    Get detailed information about a specific company.

    Args:
        company_id: Company ID

    Returns:
        {
            "id": 1,
            "name": "Company Name",
            "status": "active",
            "contact_email": "contact@example.com",
            "contact_phone": "XXX-XXX-XXXX",  # Filtered for PHI
            ...
        }

    Example:
        >>> company = get_company(1)
        >>> print(f"Company: {company['name']}")
    """
    try:
        response = call_service('codex', f'/api/company/{company_id}')
        return response.json()
    except Exception as e:
        return {
            'error': str(e),
            'id': company_id
        }


def get_tickets(
    company_id: int = None,
    status: str = None,
    limit: int = 50
) -> dict:
    """
    Get list of tickets, optionally filtered.

    Args:
        company_id: Filter by company ID (optional)
        status: Filter by status (optional): 'open', 'in_progress', 'resolved', 'closed'
        limit: Maximum number of tickets to return

    Returns:
        {
            "tickets": [
                {
                    "id": 12345,
                    "subject": "Password reset",
                    "status": "open",
                    "company_id": 1,
                    "created_at": "2025-10-21T10:00:00",
                    ...
                },
                ...
            ],
            "count": 42
        }

    Example:
        >>> tickets = get_tickets(status='open', limit=10)
        >>> print(f"Found {len(tickets['tickets'])} open tickets")
    """
    try:
        params = {'limit': limit}
        if company_id:
            params['company_id'] = company_id
        if status:
            params['status'] = status

        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        response = call_service('codex', f'/api/tickets?{query_string}')

        return response.json()
    except Exception as e:
        return {
            'error': str(e),
            'tickets': [],
            'count': 0
        }


def get_ticket(ticket_id: int) -> dict:
    """
    Get detailed information about a specific ticket.

    Args:
        ticket_id: Ticket ID

    Returns:
        {
            "id": 12345,
            "subject": "Password reset",
            "description": "User needs password reset for email account",
            "status": "open",
            "priority": "medium",
            "company_id": 1,
            "company_name": "Company Name",
            "created_at": "2025-10-21T10:00:00",
            "updated_at": "2025-10-21T11:00:00",
            "assigned_to": "Tech Name",
            "notes": [
                {"created_at": "...", "text": "..."},
                ...
            ]
        }

    Example:
        >>> ticket = get_ticket(12345)
        >>> print(f"Ticket: {ticket['subject']} - {ticket['status']}")
    """
    try:
        response = call_service('codex', f'/api/ticket/{ticket_id}')
        return response.json()
    except Exception as e:
        return {
            'error': str(e),
            'id': ticket_id
        }


def update_ticket(
    ticket_id: int,
    status: str = None,
    notes: str = None,
    assigned_to: str = None
) -> dict:
    """
    Update a ticket's status or add notes.

    Args:
        ticket_id: Ticket ID
        status: New status (optional): 'open', 'in_progress', 'resolved', 'closed'
        notes: Notes to add (optional)
        assigned_to: Assign to technician (optional)

    Returns:
        {
            "success": true,
            "ticket_id": 12345,
            "message": "Ticket updated successfully"
        }

    Example:
        >>> result = update_ticket(
        ...     12345,
        ...     status='in_progress',
        ...     notes='Working on password reset'
        ... )
        >>> print(result['message'])
    """
    try:
        data = {}
        if status:
            data['status'] = status
        if notes:
            data['notes'] = notes
        if assigned_to:
            data['assigned_to'] = assigned_to

        response = call_service(
            'codex',
            f'/api/ticket/{ticket_id}/update',
            method='POST',
            json=data
        )

        return response.json()
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'ticket_id': ticket_id
        }
