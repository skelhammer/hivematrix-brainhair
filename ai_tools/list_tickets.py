#!/usr/bin/env python3
"""
List Tickets from Codex/PSA

Retrieves and displays tickets with filtering.
"""

import json
import sys
from brainhair_auth import get_auth


def list_tickets(source="codex", company_id=None, status=None, limit=50):
    """
    List tickets with PHI/CJIS filtering.

    Args:
        source: Source of tickets ("codex" or "psa")
        company_id: Optional company ID filter
        status: Optional status filter
        limit: Maximum number of results

    Returns:
        List of tickets
    """
    auth = get_auth()
    params = {}

    if source == "psa":
        params["limit"] = str(limit)
        endpoint = "/api/psa/tickets"
    else:
        if company_id:
            params["company_id"] = company_id
        if status:
            params["status"] = status
        endpoint = "/api/codex/tickets"

    response = auth.get(endpoint, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []


def get_ticket(ticket_id, source="psa"):
    """
    Get a specific ticket.

    Args:
        ticket_id: Ticket ID
        source: Source ("psa" or "codex")

    Returns:
        Ticket details
    """
    auth = get_auth()

    endpoint = f"/api/{source}/ticket/{ticket_id}"
    response = auth.get(endpoint)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  List: python list_tickets.py list [source]")
        print("  Get:  python list_tickets.py get <ticket_id> [source]")
        print("")
        print("Sources: codex, psa")
        sys.exit(1)

    command = sys.argv[1]
    source = "psa"

    if command == "list":
        if len(sys.argv) > 2:
            source = sys.argv[2]

        tickets = list_tickets(source=source)

        print(f"\n=== Tickets from {source} ===\n")

        if isinstance(tickets, list):
            for ticket in tickets:
                if isinstance(ticket, dict):
                    print(f"ID: {ticket.get('id')}")
                    print(f"Subject: {ticket.get('subject', 'N/A')}")
                    print(f"Status: {ticket.get('status', 'N/A')}")
                    print(f"Priority: {ticket.get('priority', 'N/A')}")
                    print(f"Requester: {ticket.get('requester', 'N/A')}")
                    print(f"Created: {ticket.get('created_at', 'N/A')}")
                    print("-" * 60)
        else:
            print(json.dumps(tickets, indent=2))

        print(f"\nTotal: {len(tickets) if isinstance(tickets, list) else 'N/A'}")

    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: Ticket ID required")
            sys.exit(1)

        ticket_id = sys.argv[2]
        if len(sys.argv) > 3:
            source = sys.argv[3]

        ticket = get_ticket(ticket_id, source)

        print(f"\n=== Ticket {ticket_id} from {source} ===\n")
        print(json.dumps(ticket, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
