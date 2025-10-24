#!/usr/bin/env python3
"""Get billing info for Example Company Performance Materials"""

import json
import sys
from brainhair_auth import get_auth


def get_billing_for_company(company_name):
    """Get billing information for a specific company."""
    auth = get_auth()

    # First, find the company
    response = auth.get("/api/codex/companies", params={"filter": "phi"})
    if response.status_code != 200:
        print(f"Error getting companies: {response.status_code}")
        return None

    companies = response.json().get('data', [])
    company = None
    for c in companies:
        if c.get('name') == company_name:
            company = c
            break

    if not company:
        print(f"Company '{company_name}' not found")
        return None

    print(f"Found: {company['name']}")

    # Get account number from custom fields or metadata
    account_number = company.get('account_number')

    if not account_number:
        # Try to get from custom fields
        custom_fields = company.get('custom_fields', {})
        account_number = custom_fields.get('account_number')

    if not account_number:
        print("No account number found for this company")
        print(f"Company data: {json.dumps(company, indent=2)}")
        return None

    print(f"Account Number: {account_number}")
    print()

    # Get billing information
    response = auth.get(f"/api/billing/company/{account_number}")

    if response.status_code != 200:
        print(f"Error getting billing: {response.status_code}")
        print(response.text)
        return None

    billing = response.json()

    print("=" * 60)
    print("BILLING OVERVIEW")
    print("=" * 60)
    print(f"Company: {billing.get('company_name', 'N/A')}")
    print(f"Billing Plan: {billing.get('plan_name', 'N/A')}")
    print()

    if 'quantities' in billing:
        print("=" * 60)
        print("QUANTITIES")
        print("=" * 60)
        for key, value in billing['quantities'].items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        print()

    if 'effective_rates' in billing:
        print("=" * 60)
        print("EFFECTIVE RATES")
        print("=" * 60)
        for key, value in billing['effective_rates'].items():
            if isinstance(value, (int, float)):
                print(f"  {key.replace('_', ' ').title()}: ${value:.2f}")
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}")
        print()

    if 'receipt' in billing:
        print("=" * 60)
        print("MONTHLY BILL BREAKDOWN")
        print("=" * 60)
        receipt = billing['receipt']
        print(f"  User Charges: ${receipt.get('user_charges', 0):.2f}")
        print(f"  Asset Charges: ${receipt.get('asset_charges', 0):.2f}")
        print(f"  Prepaid Hours Value: ${receipt.get('prepaid_hours_value', 0):.2f}")
        print(f"  Additional Line Items: ${receipt.get('additional_line_items', 0):.2f}")
        print(f"  ---")
        print(f"  Subtotal: ${receipt.get('subtotal', 0):.2f}")
        print(f"  Tax: ${receipt.get('tax', 0):.2f}")
        print(f"  ---")
        print(f"  TOTAL: ${receipt.get('total', 0):.2f}")
        print()

    if billing.get('overrides'):
        print("=" * 60)
        print("CUSTOM OVERRIDES")
        print("=" * 60)
        for key, value in billing['overrides'].items():
            if isinstance(value, (int, float)):
                print(f"  {key.replace('_', ' ').title()}: ${value:.2f}")
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}")
        print()

    return billing


if __name__ == "__main__":
    company_name = sys.argv[1] if len(sys.argv) > 1 else "Example Company Performance Materials"
    get_billing_for_company(company_name)
