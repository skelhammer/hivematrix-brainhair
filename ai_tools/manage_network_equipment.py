#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Manage Network Equipment

Manages manual network equipment (switches/firewalls) for billing purposes.
This is used when equipment is not automatically detected by Codex.

Usage:
    python manage_network_equipment.py <company_name_or_account> --add switch "Core Switch 1"
    python manage_network_equipment.py <company_name_or_account> --add firewall "Perimeter Firewall"
    python manage_network_equipment.py <company_name_or_account> --list
    python manage_network_equipment.py <company_name_or_account> --remove 123
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


def list_manual_assets(account_number):
    """List all manual network equipment."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{LEDGER_URL}/api/overrides/manual-assets/{account_number}",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            assets = data.get('manual_assets', [])

            # Filter for network equipment only
            network_assets = [a for a in assets if a['billing_type'].lower() in ['switch', 'firewall']]
            return network_assets
        else:
            print(f"ERROR: Failed to fetch manual assets: {response.status_code}")
            return None

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def add_network_equipment(account_number, equipment_type, hostname):
    """Add a network equipment item."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Capitalize equipment type
    equipment_type = equipment_type.capitalize()

    try:
        response = requests.post(
            f"{LEDGER_URL}/api/overrides/manual-assets/{account_number}",
            json={
                'hostname': hostname,
                'billing_type': equipment_type,
                'notes': f'Manual network equipment added via brainhair tools'
            },
            headers=headers,
            timeout=5
        )

        if response.status_code == 201:
            return True
        else:
            print(f"ERROR: Failed to add equipment: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def remove_network_equipment(account_number, asset_id):
    """Remove a network equipment item."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.delete(
            f"{LEDGER_URL}/api/overrides/manual-assets/{account_number}/{asset_id}",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            return True
        else:
            print(f"ERROR: Failed to remove equipment: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Manage network equipment for billing')
    parser.add_argument('company', help='Company name or account number')
    parser.add_argument('--list', action='store_true', help='List all network equipment')
    parser.add_argument('--add', nargs=2, metavar=('TYPE', 'NAME'),
                        help='Add network equipment (type: switch/firewall, name: hostname)')
    parser.add_argument('--remove', type=int, metavar='ID', help='Remove equipment by ID')

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

    # List equipment
    if args.list or (not args.add and not args.remove):
        print("Network Equipment:")
        print("=" * 70)
        assets = list_manual_assets(account_number)

        if assets is None:
            sys.exit(1)

        if not assets:
            print("No manual network equipment configured")
        else:
            switches = [a for a in assets if a['billing_type'].lower() == 'switch']
            firewalls = [a for a in assets if a['billing_type'].lower() == 'firewall']

            if switches:
                print("\nSwitches:")
                for s in switches:
                    print(f"  [{s['id']}] {s['hostname']}")

            if firewalls:
                print("\nFirewalls:")
                for f in firewalls:
                    print(f"  [{f['id']}] {f['hostname']}")

            print(f"\nTotal: {len(switches)} switches, {len(firewalls)} firewalls")
        print("=" * 70)

    # Add equipment
    if args.add:
        equipment_type, hostname = args.add

        if equipment_type.lower() not in ['switch', 'firewall']:
            print("ERROR: Equipment type must be 'switch' or 'firewall'")
            sys.exit(1)

        print(f"Adding {equipment_type}: {hostname}")

        # Request approval
        approved = request_approval(
            f"Add {equipment_type} to {company['name']}",
            {
                'Company': company['name'],
                'Account': str(account_number),
                'Equipment Type': equipment_type.capitalize(),
                'Hostname': hostname
            }
        )

        if not approved:
            print("✗ User denied the change")
            sys.exit(1)

        if add_network_equipment(account_number, equipment_type, hostname):
            print(f"✓ {equipment_type.capitalize()} added successfully")
        else:
            print(f"✗ Failed to add {equipment_type}")
            sys.exit(1)

    # Remove equipment
    if args.remove:
        asset_id = args.remove
        print(f"Removing equipment ID {asset_id}")

        # Request approval
        approved = request_approval(
            f"Remove equipment from {company['name']}",
            {
                'Company': company['name'],
                'Account': str(account_number),
                'Equipment ID': str(asset_id)
            }
        )

        if not approved:
            print("✗ User denied the change")
            sys.exit(1)

        if remove_network_equipment(account_number, asset_id):
            print(f"✓ Equipment removed successfully")
        else:
            print(f"✗ Failed to remove equipment")
            sys.exit(1)


if __name__ == "__main__":
    main()
