#!/usr/bin/env python3
"""
Update Billing Settings

Updates per-unit rates and line items for a company's billing.
This is used when aligning billing with contract terms.

Usage:
    python update_billing.py <company_name_or_account> --per-user 125 --per-server 125
    python update_billing.py 123456 --per-user 125 --per-server 125 --per-workstation 0
    python update_billing.py "Example Company" --line-item "Network Management" 200
"""

import sys
import os
import json
import requests
import argparse

# Import approval helper
sys.path.insert(0, os.path.dirname(__file__))
from approval_helper import request_approval

# Service URLs
CORE_URL = os.getenv('CORE_SERVICE_URL', 'http://localhost:5000')
LEDGER_URL = os.getenv('LEDGER_SERVICE_URL', 'http://localhost:5030')
CODEX_URL = os.getenv('CODEX_SERVICE_URL', 'http://localhost:5010')


def get_service_token(target_service):
    """Get service token from Core."""
    try:
        response = requests.post(
            f"{CORE_URL}/service-token",
            json={
                "calling_service": "brainhair",
                "target_service": target_service
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["token"]
        return None
    except Exception:
        return None


def find_company(search_term):
    """Find company by name or account number."""
    token = get_service_token("codex")
    if not token:
        print("ERROR: Could not get service token for Codex")
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{CODEX_URL}/api/companies", headers=headers, timeout=5)
        if response.status_code != 200:
            print(f"ERROR: Could not fetch companies: {response.status_code}")
            return None

        companies = response.json()

        # Try exact account number match first
        for company in companies:
            if str(company.get('account_number')) == str(search_term):
                return company

        # Try name match (case-insensitive)
        search_lower = search_term.lower()
        for company in companies:
            if search_lower in company.get('name', '').lower():
                return company

        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def update_rates(account_number, rates):
    """Update per-unit billing rates."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # First get current overrides
        response = requests.get(
            f"{LEDGER_URL}/api/overrides/client/{account_number}",
            headers=headers,
            timeout=5
        )

        current_overrides = {}
        if response.status_code == 200:
            current_overrides = response.json()

        # Merge with new rates
        updated_overrides = {**current_overrides, **rates}

        # Update overrides
        response = requests.put(
            f"{LEDGER_URL}/api/overrides/client/{account_number}",
            json=updated_overrides,
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            return True
        else:
            print(f"ERROR: Failed to update rates: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def add_line_item(account_number, name, monthly_fee, description=""):
    """Add a recurring line item (fixed monthly charge)."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Check if line item already exists
        response = requests.get(
            f"{LEDGER_URL}/api/overrides/line-items/{account_number}",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            existing_items = response.json().get('line_items', [])
            for item in existing_items:
                if item.get('name') == name:
                    print(f"Line item '{name}' already exists, updating...")
                    # Update existing
                    response = requests.put(
                        f"{LEDGER_URL}/api/overrides/line-items/{account_number}/{item['id']}",
                        json={
                            'monthly_fee': monthly_fee,
                            'description': description
                        },
                        headers=headers,
                        timeout=5
                    )
                    return response.status_code == 200

        # Create new line item
        response = requests.post(
            f"{LEDGER_URL}/api/overrides/line-items/{account_number}",
            json={
                'name': name,
                'monthly_fee': monthly_fee,
                'description': description
            },
            headers=headers,
            timeout=5
        )

        if response.status_code in [200, 201]:
            return True
        else:
            print(f"ERROR: Failed to add line item: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def get_billing(account_number):
    """Get current billing to verify changes."""
    token = get_service_token("ledger")
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{LEDGER_URL}/api/billing/{account_number}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Update billing settings for a company')
    parser.add_argument('company', help='Company name or account number')
    parser.add_argument('--per-user', type=float, help='Cost per user per month')
    parser.add_argument('--per-workstation', type=float, help='Cost per workstation per month')
    parser.add_argument('--per-server', type=float, help='Cost per server per month')
    parser.add_argument('--per-vm', type=float, help='Cost per VM per month')
    parser.add_argument('--per-switch', type=float, help='Cost per switch per month')
    parser.add_argument('--per-firewall', type=float, help='Cost per firewall per month')
    parser.add_argument('--per-hour', type=float, help='Cost per hour of support')
    parser.add_argument('--prepaid-hours', type=float, help='Prepaid hours per month')
    parser.add_argument('--billing-plan', type=str,
                        choices=['[PLAN-D]', '[PLAN-C]', '[PLAN-B]', '[PLAN-A]',
                                '[PLAN-E]', '[PLAN-F]', 'Break Fix', '[PLAN-G]'],
                        help='Set billing plan type')
    parser.add_argument('--contract-term', type=str,
                        choices=['Month to Month', '1-Year', '2-Year', '3-Year'],
                        help='Set contract term length')
    parser.add_argument('--line-item', nargs=2, metavar=('NAME', 'AMOUNT'),
                        help='Add recurring line item (name and monthly amount)')

    args = parser.parse_args()

    # Find company
    print(f"Searching for company: {args.company}")
    company = find_company(args.company)

    if not company:
        print(f"ERROR: Company not found: {args.company}")
        sys.exit(1)

    account_number = company.get('account_number')
    company_name = company.get('name')
    print(f"Found: {company_name} (Account: {account_number})\n")

    # Get current billing
    print("Current billing:")
    current_billing = get_billing(account_number)
    if current_billing:
        rates = current_billing.get('effective_rates', {})
        print(f"  Per user: ${rates.get('per_user_cost', 0):.2f}")
        print(f"  Per workstation: ${rates.get('per_workstation_cost', 0):.2f}")
        print(f"  Per server: ${rates.get('per_server_cost', 0):.2f}")
        print(f"  Per VM: ${rates.get('per_vm_cost', 0):.2f}")
        print(f"  Per hour: ${rates.get('per_hour_ticket_cost', 0):.2f}")
        print(f"  Current total: ${current_billing.get('receipt', {}).get('total', 0):.2f}\n")

    # Update rates
    rates_to_update = {}
    if args.per_user is not None:
        rates_to_update['per_user_cost'] = args.per_user
    if args.per_workstation is not None:
        rates_to_update['per_workstation_cost'] = args.per_workstation
    if args.per_server is not None:
        rates_to_update['per_server_cost'] = args.per_server
    if args.per_vm is not None:
        rates_to_update['per_vm_cost'] = args.per_vm
    if args.per_switch is not None:
        rates_to_update['per_switch_cost'] = args.per_switch
    if args.per_firewall is not None:
        rates_to_update['per_firewall_cost'] = args.per_firewall
    if args.per_hour is not None:
        rates_to_update['per_hour_ticket_cost'] = args.per_hour
    if args.prepaid_hours is not None:
        rates_to_update['prepaid_hours_monthly'] = args.prepaid_hours
    if args.billing_plan is not None:
        rates_to_update['billing_plan'] = args.billing_plan
    if args.contract_term is not None:
        rates_to_update['term_length'] = args.contract_term

    if rates_to_update:
        print("Updating rates...")
        for key, value in rates_to_update.items():
            if key in ['billing_plan', 'term_length']:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: ${value:.2f}")

        # Request approval
        approval_details = {
            'Company': company['name'],
            'Account': str(account_number)
        }
        for key, value in rates_to_update.items():
            if key in ['billing_plan', 'term_length']:
                approval_details[key.replace('_', ' ').title()] = value
            else:
                approval_details[key.replace('_', ' ').title()] = f"${value:.2f}"

        approved = request_approval(
            f"Update billing rates for {company['name']}",
            approval_details
        )

        if not approved:
            print("✗ User denied the change")
            sys.exit(1)

        if update_rates(account_number, rates_to_update):
            print("✓ Rates updated successfully\n")
        else:
            print("✗ Failed to update rates\n")
            sys.exit(1)

    # Add line item
    if args.line_item:
        name, amount = args.line_item
        amount = float(amount)
        print(f"Adding line item: {name} @ ${amount:.2f}/month...")

        # Request approval
        approved = request_approval(
            f"Add line item to {company['name']}",
            {
                'Company': company['name'],
                'Account': str(account_number),
                'Line Item': name,
                'Monthly Fee': f"${amount:.2f}"
            }
        )

        if not approved:
            print("✗ User denied the change")
            sys.exit(1)

        if add_line_item(account_number, name, amount):
            print("✓ Line item added successfully\n")
        else:
            print("✗ Failed to add line item\n")
            sys.exit(1)

    # Show new billing
    print("=" * 70)
    print("Updated billing:")
    new_billing = get_billing(account_number)
    if new_billing:
        rates = new_billing.get('effective_rates', {})
        quantities = new_billing.get('quantities', {})
        receipt = new_billing.get('receipt', {})

        print(f"\nRates:")
        print(f"  Per user: ${rates.get('per_user_cost', 0):.2f}")
        print(f"  Per workstation: ${rates.get('per_workstation_cost', 0):.2f}")
        print(f"  Per server: ${rates.get('per_server_cost', 0):.2f}")
        print(f"  Per VM: ${rates.get('per_vm_cost', 0):.2f}")
        print(f"  Per switch: ${rates.get('per_switch_cost', 0):.2f}")
        print(f"  Per firewall: ${rates.get('per_firewall_cost', 0):.2f}")

        print(f"\nCurrent quantities:")
        print(f"  Users: {quantities.get('regular_users', 0)}")
        print(f"  Workstations: {quantities.get('workstation', 0)}")
        print(f"  Servers: {quantities.get('server', 0)}")
        print(f"  VMs: {quantities.get('vm', 0)}")
        print(f"  Switches: {quantities.get('switch', 0)}")
        print(f"  Firewalls: {quantities.get('firewall', 0)}")

        print(f"\nCharges:")
        print(f"  Users: ${receipt.get('total_user_charges', 0):.2f}")
        print(f"  Assets: ${receipt.get('total_asset_charges', 0):.2f}")
        print(f"  Tickets: ${receipt.get('ticket_charge', 0):.2f}")
        print(f"  Backup: ${receipt.get('backup_charge', 0):.2f}")

        print(f"\n  TOTAL: ${receipt.get('total', 0):.2f}")
        print("=" * 70)


if __name__ == "__main__":
    main()
