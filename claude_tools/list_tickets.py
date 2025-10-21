#!/usr/bin/env python3
"""
List tickets from Codex.

Usage: ./list_tickets.py [--status STATUS] [--company COMPANY_ID] [--limit N]
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.flaskenv'))

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app
from app.service_client import call_service
from app.presidio_filter import filter_data

def list_tickets(status=None, company_id=None, limit=10):
    """List tickets with optional filters."""
    with app.app_context():
        try:
            params = {'limit': limit}
            if status:
                params['status'] = status
            if company_id:
                params['company_id'] = company_id

            query_string = '&'.join(f'{k}={v}' for k, v in params.items())
            response = call_service('codex', f'/api/tickets?{query_string}')
            data = response.json()

            if 'error' in data:
                print(f"Error: {data['error']}")
                return

            # Filter PHI/CJIS data before showing to Claude
            data = filter_data(data)

            tickets = data.get('tickets', [])
            total = data.get('total', 0)

            print(f"\nFound {total} total tickets, showing {len(tickets)}:\n")

            for ticket in tickets:
                print(f"#{ticket['id']}: {ticket['subject']}")
                print(f"  Status: {ticket['status']} | Priority: {ticket['priority']}")
                print(f"  Company: {ticket.get('company_id', 'N/A')}")
                print(f"  Updated: {ticket.get('last_updated_at', 'N/A')}")
                print()

        except Exception as e:
            print(f"Error listing tickets: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List tickets from Codex')
    parser.add_argument('--status', help='Filter by status (open, closed, etc)')
    parser.add_argument('--company', help='Filter by company ID')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number to return')

    args = parser.parse_args()
    list_tickets(status=args.status, company_id=args.company, limit=args.limit)
