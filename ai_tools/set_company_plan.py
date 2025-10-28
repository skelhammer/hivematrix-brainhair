#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Set Company Billing Plan

Sets a company's billing plan and contract term. This will:
1. Update the plan in Codex (customer data)
2. Apply the plan's rates as overrides in Ledger (billing system)

Usage:
    python set_company_plan.py <company_name_or_account> <plan_name> <term_length>
    python set_company_plan.py "Example Company" "[PLAN-A]" "2-Year"
    python set_company_plan.py 123456 "[PLAN-B]" "Month to Month"

Available Plans: Break Fix, [PLAN-D], [PLAN-C], [PLAN-B], [PLAN-A], [PLAN-E], [PLAN-F], [PLAN-G]
Available Terms: Month to Month, 1-Year, 2-Year, 3-Year
"""

import sys
import os
import json
import requests

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
    except:
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


def get_billing_plan(plan_name, term_length):
    """Get billing plan from Codex."""
    token = get_service_token("codex")
    if not token:
        print("ERROR: Could not get service token for Codex")
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{CODEX_URL}/api/billing-plans",
            params={'plan_name': plan_name, 'term_length': term_length},
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            print(f"ERROR: Could not fetch billing plan: {response.status_code}")
            return None

        plans = response.json()
        if not plans:
            print(f"ERROR: Plan not found: {plan_name} ({term_length})")
            return None

        return plans[0]

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def apply_plan_to_ledger(account_number, plan):
    """Apply plan rates to Ledger as billing overrides."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Build override dict from plan
    overrides = {
        'billing_plan': plan['plan_name'],
        'term_length': plan['term_length'],
        'per_user_cost': plan['per_user_cost'],
        'per_workstation_cost': plan['per_workstation_cost'],
        'per_server_cost': plan['per_server_cost'],
        'per_vm_cost': plan['per_vm_cost'],
        'per_switch_cost': plan['per_switch_cost'],
        'per_firewall_cost': plan['per_firewall_cost'],
        'per_hour_ticket_cost': plan['per_hour_ticket_cost'],
        'backup_base_fee_workstation': plan['backup_base_fee_workstation'],
        'backup_base_fee_server': plan['backup_base_fee_server'],
        'backup_cost_per_gb_workstation': plan['backup_cost_per_gb_workstation'],
        'backup_cost_per_gb_server': plan['backup_cost_per_gb_server']
    }

    try:
        # Get current overrides
        response = requests.get(
            f"{LEDGER_URL}/api/overrides/client/{account_number}",
            headers=headers,
            timeout=5
        )

        current_overrides = {}
        if response.status_code == 200:
            current_overrides = response.json()

        # Merge with new overrides
        updated_overrides = {**current_overrides, **overrides}

        # Update Ledger
        response = requests.put(
            f"{LEDGER_URL}/api/overrides/client/{account_number}",
            json=updated_overrides,
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            return True
        else:
            print(f"ERROR: Failed to update Ledger: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    if len(sys.argv) < 4:
        print("Usage: python set_company_plan.py <company_name_or_account> <plan_name> <term_length>")
        print("Example: python set_company_plan.py 'Example Company' '[PLAN-A]' '2-Year'")
        print("\nAvailable Plans: Break Fix, [PLAN-D], [PLAN-C], [PLAN-B], [PLAN-A], [PLAN-E], [PLAN-F], [PLAN-G]")
        print("Available Terms: Month to Month, 1-Year, 2-Year, 3-Year")
        sys.exit(1)

    company_search = sys.argv[1]
    plan_name = sys.argv[2]
    term_length = sys.argv[3]

    # Find company
    print(f"Searching for company: {company_search}")
    company = find_company(company_search)

    if not company:
        print(f"ERROR: Company not found: {company_search}")
        sys.exit(1)

    account_number = company.get('account_number')
    company_name = company.get('name')
    print(f"Found: {company_name} (Account: {account_number})\n")

    # Get billing plan
    print(f"Looking up plan: {plan_name} ({term_length})")
    plan = get_billing_plan(plan_name, term_length)

    if not plan:
        sys.exit(1)

    print(f"Found plan with rates:")
    print(f"  Per user: ${plan['per_user_cost']:.2f}")
    print(f"  Per workstation: ${plan['per_workstation_cost']:.2f}")
    print(f"  Per server: ${plan['per_server_cost']:.2f}")
    print(f"  Per VM: ${plan['per_vm_cost']:.2f}")
    print(f"  Per switch: ${plan['per_switch_cost']:.2f}")
    print(f"  Per firewall: ${plan['per_firewall_cost']:.2f}")
    print(f"  Per hour: ${plan['per_hour_ticket_cost']:.2f}")
    print(f"  Support: {plan['support_level']}")
    print(f"  Features: {plan['antivirus']}, {plan['soc']}, {plan['password_manager']}")
    print()

    # Request approval
    approved = request_approval(
        f"Set billing plan for {company_name}",
        {
            'Company': company_name,
            'Account': str(account_number),
            'Plan': plan_name,
            'Term': term_length,
            'Per User': f"${plan['per_user_cost']:.2f}",
            'Per Server': f"${plan['per_server_cost']:.2f}",
            'Per Workstation': f"${plan['per_workstation_cost']:.2f}"
        }
    )

    if not approved:
        print("✗ User denied the change")
        sys.exit(1)

    # Apply to Ledger
    print(f"Applying plan to Ledger...")
    if apply_plan_to_ledger(account_number, plan):
        print(f"✓ Plan applied successfully!")
        print(f"\n{company_name} is now on {plan_name} ({term_length})")
    else:
        print(f"✗ Failed to apply plan")
        sys.exit(1)


if __name__ == "__main__":
    main()
