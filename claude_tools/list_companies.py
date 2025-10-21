#!/usr/bin/env python3
"""
List companies from Codex.

Usage: ./list_companies.py [--limit N]
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

def list_companies(limit=20):
    """List companies."""
    with app.app_context():
        try:
            response = call_service('codex', f'/api/companies?limit={limit}')
            companies = response.json()

            if isinstance(companies, dict) and 'error' in companies:
                print(f"Error: {companies['error']}")
                return

            # Filter PHI/CJIS data before showing to Claude
            companies = filter_data(companies)

            print(f"\nShowing {len(companies)} companies:\n")

            for company in companies:
                print(f"{company['account_number']}: {company['name']}")
                if company.get('description'):
                    desc = company['description'][:80]
                    print(f"  {desc}{'...' if len(company['description']) > 80 else ''}")
                print()

        except Exception as e:
            print(f"Error listing companies: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List companies from Codex')
    parser.add_argument('--limit', type=int, default=20, help='Maximum number to return')

    args = parser.parse_args()
    list_companies(limit=args.limit)
