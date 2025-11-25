#!/usr/bin/env python3
"""
List Companies from Codex

Retrieves and displays all companies from the Codex database.
"""

import json
import sys
from brainhair_auth import get_auth


def list_companies(filter_type="phi"):
    """
    List all companies with PHI/CJIS filtering.

    Args:
        filter_type: Type of filter to apply ("phi" or "cjis")

    Returns:
        List of companies
    """
    auth = get_auth()

    response = auth.get("/api/codex/companies", params={"filter": filter_type})

    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []


def main():
    """Main entry point."""
    filter_type = sys.argv[1] if len(sys.argv) > 1 else "phi"
    companies = list_companies(filter_type)

    print(f"\n=== Companies (Filter: {filter_type}) ===\n")

    if isinstance(companies, list):
        for company in companies:
            if isinstance(company, dict):
                print(f"ID: {company.get('id')}")
                print(f"Name: {company.get('name')}")
                print(f"Domain: {company.get('domain', 'N/A')}")
                print(f"Status: {company.get('status', 'N/A')}")
                print("-" * 40)
    else:
        print(json.dumps(companies, indent=2))

    print(f"\nTotal: {len(companies) if isinstance(companies, list) else 'N/A'}")


if __name__ == "__main__":
    main()
