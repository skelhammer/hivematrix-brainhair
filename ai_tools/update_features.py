#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Update feature overrides for a company in Ledger.

This allows you to customize which features (Antivirus, SOC, Password Manager, etc.)
are included for a specific company, overriding the default plan features from Codex.

Usage:
    python ai_tools/update_features.py <company_name_or_account_number> --antivirus "SentinelOne"
    python ai_tools/update_features.py "Example Company" --soc "RocketCyber" --antivirus "Webroot"
    python ai_tools/update_features.py 123456 --password-manager "Keeper" --sat "Datto SAT"
    python ai_tools/update_features.py "Example Company" --list

Available features:
    --antivirus (e.g., "SentinelOne", "Webroot", "Not Included")
    --soc (e.g., "RocketCyber", "Not Included")
    --password-manager (e.g., "Keeper", "Not Included")
    --sat (e.g., "Datto SAT", "Not Included")
    --email-security (e.g., "Mimecast", "Not Included")
    --network-management (e.g., "Datto Network Management", "Not Included")
    --list (show current feature overrides)
"""

import sys
import os
import json
import requests
import argparse

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
        print(f"ERROR: Could not search for company: {e}")
        return None

def list_feature_overrides(account_number):
    """List current feature overrides for a company."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{LEDGER_URL}/api/overrides/features/{account_number}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            overrides = data.get('feature_overrides', [])

            if not overrides:
                print("\nNo feature overrides configured. Using plan defaults from Codex.")
                return True

            print("\n" + "=" * 70)
            print("FEATURE OVERRIDES")
            print("=" * 70)
            for override in overrides:
                status = "✓ ENABLED" if override['override_enabled'] else "  disabled"
                feature_name = override['feature_type'].replace('_', ' ').title()
                print(f"{status:12s} {feature_name:20s} {override['value']}")
            print("=" * 70)
            return True
        else:
            print(f"ERROR: Could not fetch feature overrides (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def update_features(account_number, feature_updates):
    """Update feature overrides in Ledger."""
    token = get_service_token("ledger")
    if not token:
        print("ERROR: Could not get service token for Ledger")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.put(
            f"{LEDGER_URL}/api/overrides/features/{account_number}",
            json=feature_updates,
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            return True
        else:
            print(f"ERROR: Failed to update features (HTTP {response.status_code})")
            print(response.text)
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Update feature overrides for a company in Ledger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_tools/update_features.py "Example Company" --antivirus "SentinelOne"
  python ai_tools/update_features.py 123456 --soc "RocketCyber" --password-manager "Keeper"
  python ai_tools/update_features.py "Example Company" --list

Available feature values (examples):
  Antivirus: SentinelOne, Webroot, Not Included
  SOC: RocketCyber, Not Included
  Password Manager: Keeper, Not Included
  SAT: Datto SAT, Not Included
  Email Security: Mimecast, Not Included
  Network Management: Datto Network Management, Not Included
        """
    )

    parser.add_argument('company', help='Company name or account number')
    parser.add_argument('--list', action='store_true', help='List current feature overrides')
    parser.add_argument('--antivirus', type=str, help='Antivirus solution')
    parser.add_argument('--soc', type=str, help='SOC/Security monitoring')
    parser.add_argument('--password-manager', type=str, help='Password manager')
    parser.add_argument('--sat', type=str, help='Security Awareness Training')
    parser.add_argument('--email-security', type=str, help='Email security')
    parser.add_argument('--network-management', type=str, help='Network management')

    args = parser.parse_args()

    # Find company
    print(f"Searching for company: {args.company}")
    company = find_company(args.company)

    if not company:
        print(f"ERROR: Company not found: {args.company}")
        sys.exit(1)

    account_number = company.get('account_number')
    print(f"Found: {company.get('name')} (Account: {account_number})\n")

    # List mode
    if args.list:
        list_feature_overrides(account_number)
        sys.exit(0)

    # Build feature updates
    feature_updates = {}

    if args.antivirus:
        feature_updates['antivirus'] = args.antivirus
    if args.soc:
        feature_updates['soc'] = args.soc
    if args.password_manager:
        feature_updates['password_manager'] = args.password_manager
    if args.sat:
        feature_updates['sat'] = args.sat
    if args.email_security:
        feature_updates['email_security'] = args.email_security
    if args.network_management:
        feature_updates['network_management'] = args.network_management

    if not feature_updates:
        print("ERROR: No feature updates provided. Use --help for usage.")
        sys.exit(1)

    # Display what we're updating
    print("Updating features:")
    for feature, value in feature_updates.items():
        feature_name = feature.replace('_', ' ').title()
        print(f"  {feature_name}: {value}")
    print()

    # Update
    if update_features(account_number, feature_updates):
        print("✓ Feature overrides updated successfully")
        print("\nNote: These overrides will be applied on top of the plan defaults from Codex.")
    else:
        print("✗ Failed to update feature overrides")
        sys.exit(1)

if __name__ == "__main__":
    main()
