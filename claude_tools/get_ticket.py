#!/usr/bin/env python3
"""
Get ticket details from Codex.

Usage: ./get_ticket.py <ticket_id>
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.flaskenv'))

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app
from app.service_client import call_service
from app.presidio_filter import filter_by_compliance_level
import json

def get_ticket(ticket_id):
    """Get ticket details."""
    with app.app_context():
        try:
            response = call_service('codex', f'/api/ticket/{ticket_id}')
            ticket = response.json()

            if 'error' in ticket:
                print(f"Error: {ticket['error']}")
                return

            # Get company compliance level and apply appropriate filtering
            compliance_level = ticket.get('company_compliance_level', 'standard')
            ticket = filter_by_compliance_level(ticket, compliance_level)

            # Print formatted ticket info
            print(f"\nTicket #{ticket['id']}")
            print(f"Subject: {ticket['subject']}")
            print(f"Status: {ticket['status']}")
            print(f"Priority: {ticket['priority']}")
            print(f"Company: {ticket.get('company_name', 'N/A')}")
            print(f"Requester: {ticket['requester_name']} ({ticket['requester_email']})")
            print(f"Created: {ticket['created_at']}")
            print(f"Updated: {ticket['last_updated_at']}")

            if ticket.get('description_text'):
                print(f"\nDescription:")
                print(ticket['description_text'][:500])
                if len(ticket['description_text']) > 500:
                    print("...")

            if ticket.get('notes'):
                print(f"\nNotes ({len(ticket['notes'])} total):")
                for note in ticket['notes'][:3]:  # Show last 3 notes
                    print(f"  - [{note.get('created_at', 'N/A')}] {note.get('text', '')[:100]}")

        except Exception as e:
            print(f"Error getting ticket: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ./get_ticket.py <ticket_id>")
        sys.exit(1)

    ticket_id = sys.argv[1]
    get_ticket(ticket_id)
