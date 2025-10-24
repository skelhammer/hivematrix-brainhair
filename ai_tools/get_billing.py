#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Get billing information for a company.

Usage:
    python ai_tools/get_billing.py <company_name_or_account_number>
    python ai_tools/get_billing.py "Example Company"
    python ai_tools/get_billing.py 123456
"""

import sys
import os
import json
import requests

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
    except:
        return None

def find_company(search_term):
    """Find company by name or account number."""
    token = get_service_token("codex")
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{CODEX_URL}/api/companies", headers=headers, timeout=5)
        if response.status_code != 200:
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
    except:
        return None

def get_billing(account_number):
    """Get billing data from Ledger."""
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
    except:
        return None

def format_billing(billing_data):
    """Format billing data for display."""
    if not billing_data:
        return "No billing data available"

    company_name = billing_data.get('company_name', 'Unknown')
    account_number = billing_data.get('account_number', 'Unknown')
    period = billing_data.get('billing_period', 'Unknown')

    receipt = billing_data.get('receipt', {})
    total = receipt.get('total', 0)

    quantities = billing_data.get('quantities', {})
    rates = billing_data.get('effective_rates', {})

    output = []
    output.append("=" * 70)
    output.append(f"BILLING INFORMATION: {company_name}")
    output.append("=" * 70)
    output.append(f"Account Number: {account_number}")
    output.append(f"Billing Period: {period}")
    output.append(f"\nTOTAL BILL: ${total:,.2f}")
    output.append("\n" + "-" * 70)
    output.append("BREAKDOWN:")
    output.append("-" * 70)

    # Users
    user_count = quantities.get('regular_users', 0)
    user_rate = rates.get('per_user_cost', 0)
    user_total = receipt.get('total_user_charges', 0)
    output.append(f"Users:        {user_count:3d} @ ${user_rate:6.2f} = ${user_total:8.2f}")

    # Workstations
    ws_count = quantities.get('workstation', 0)
    ws_rate = rates.get('per_workstation_cost', 0)
    output.append(f"Workstations: {ws_count:3d} @ ${ws_rate:6.2f}")

    # Servers
    srv_count = quantities.get('server', 0)
    srv_rate = rates.get('per_server_cost', 0)
    output.append(f"Servers:      {srv_count:3d} @ ${srv_rate:6.2f}")

    # VMs
    vm_count = quantities.get('vm', 0)
    vm_rate = rates.get('per_vm_cost', 0)
    output.append(f"VMs:          {vm_count:3d} @ ${vm_rate:6.2f}")

    # Switches
    switch_count = quantities.get('switch', 0)
    switch_rate = rates.get('per_switch_cost', 0)
    output.append(f"Switches:     {switch_count:3d} @ ${switch_rate:6.2f}")

    # Firewalls
    firewall_count = quantities.get('firewall', 0)
    firewall_rate = rates.get('per_firewall_cost', 0)
    output.append(f"Firewalls:    {firewall_count:3d} @ ${firewall_rate:6.2f}")

    # Total assets
    asset_total = receipt.get('total_asset_charges', 0)
    output.append(f"Asset Total:                    ${asset_total:8.2f}")

    # Tickets
    hours = receipt.get('billable_hours', 0)
    hour_rate = rates.get('per_hour_ticket_cost', 0)
    ticket_total = receipt.get('ticket_charge', 0)
    output.append(f"\nTickets:      {hours:5.1f} hrs @ ${hour_rate:6.2f} = ${ticket_total:8.2f}")

    # Backup
    backup_total = receipt.get('backup_charge', 0)
    if backup_total > 0:
        output.append(f"Backup:                          ${backup_total:8.2f}")

    # Line items (from receipt data)
    line_items = receipt.get('billed_line_items', [])
    line_item_total = receipt.get('total_line_item_charges', 0)

    if line_items and line_item_total > 0:
        output.append("\n" + "-" * 70)
        output.append("LINE ITEMS (Recurring):")
        output.append("-" * 70)
        for item in line_items:
            cost = item.get('cost', 0)
            item_type = item.get('type', 'monthly')
            output.append(f"{item.get('name', 'Unknown'):30s} ${cost:8.2f} ({item_type})")
        output.append(f"{'Line Items Total:':30s} ${line_item_total:8.2f}")

    # Plan info
    output.append("\n" + "-" * 70)
    output.append("PLAN DETAILS:")
    output.append("-" * 70)
    output.append(f"Billing Plan:  {rates.get('billing_plan', 'N/A')}")
    output.append(f"Contract Term: {rates.get('term_length', 'N/A')}")
    output.append(f"Support Level: {rates.get('support_level', 'N/A')}")

    prepaid = rates.get('prepaid_hours_monthly', 0)
    if prepaid > 0:
        output.append(f"Prepaid Hours: {prepaid:.1f} hours/month")

    # Plan features
    plan_features = billing_data.get('plan_features', {})
    feature_override_status = billing_data.get('feature_override_status', {})

    if plan_features and any(v != 'Not Included' for v in plan_features.values()):
        output.append("\n" + "-" * 70)
        output.append("INCLUDED FEATURES:")
        output.append("-" * 70)
        for feature, value in plan_features.items():
            if value and value != 'Not Included':
                feature_name = feature.replace('_', ' ').title()
                # Mark overridden features with an asterisk
                override_marker = " *" if feature_override_status.get(feature, False) else ""
                output.append(f"{feature_name:20s} {value}{override_marker}")

        # Add legend if any features are overridden
        if any(feature_override_status.values()):
            output.append("")
            output.append("* = Overridden in Ledger (differs from Codex plan default)")

    output.append("=" * 70)

    return "\n".join(output)

def main():
    if len(sys.argv) < 2:
        print("Usage: python get_billing.py <company_name_or_account_number>")
        print("Example: python get_billing.py 'Example Company'")
        print("Example: python get_billing.py 123456")
        sys.exit(1)

    search_term = sys.argv[1]

    # Find company
    print(f"Searching for company: {search_term}")
    company = find_company(search_term)

    if not company:
        print(f"ERROR: Company not found: {search_term}")
        sys.exit(1)

    account_number = company.get('account_number')
    print(f"Found: {company.get('name')} (Account: {account_number})\n")

    # Get billing
    billing_data = get_billing(account_number)

    if not billing_data:
        print(f"ERROR: Could not retrieve billing data for account {account_number}")
        sys.exit(1)

    # Display
    print(format_billing(billing_data))

if __name__ == "__main__":
    main()
