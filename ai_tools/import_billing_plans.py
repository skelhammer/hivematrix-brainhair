#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Import Billing Plans from JSON

Imports billing plans, features, and users from a JSON configuration.
This is used to bulk-load default billing plans into Codex.

Usage:
    # From file
    python import_billing_plans.py plans_config.json

    # From stdin (paste JSON directly)
    python import_billing_plans.py --stdin
    echo '{"default_plans_data": [...]}' | python import_billing_plans.py --stdin

JSON Format:
{
    "default_plans_data": [
        ["Plan Name", "Term", per_user, per_workstation, per_server, per_vm,
         per_switch, per_firewall, per_hour, backup_base_ws, backup_base_srv,
         backup_gb_ws, backup_gb_srv, "Support Level", "Antivirus", "SOC",
         "Password Manager", "SAT", "Email Security", "Network Management"]
    ],
    "default_features": [
        ["Feature Type", "Feature Value"]
    ],
    "default_users": [
        ["Name", "Role", "Username"]
    ]
}
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
    except Exception as e:
        print(f"ERROR: Could not get service token: {e}")
        return None


def import_billing_plans(plans_data):
    """Import billing plans into Codex."""
    token = get_service_token("codex")
    if not token:
        print("ERROR: Could not get service token for Codex")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    imported_count = 0
    failed_count = 0

    for plan in plans_data:
        if len(plan) < 20:
            print(f"WARNING: Skipping invalid plan data (not enough fields): {plan[0] if plan else 'unknown'}")
            failed_count += 1
            continue

        # Parse plan data
        plan_data = {
            'plan_name': plan[0],
            'term_length': plan[1],
            'per_user_cost': float(plan[2]),
            'per_workstation_cost': float(plan[3]),
            'per_server_cost': float(plan[4]),
            'per_vm_cost': float(plan[5]),
            'per_switch_cost': float(plan[6]),
            'per_firewall_cost': float(plan[7]),
            'per_hour_ticket_cost': float(plan[8]),
            'backup_base_fee_workstation': float(plan[9]),
            'backup_base_fee_server': float(plan[10]),
            'backup_cost_per_gb_workstation': float(plan[11]),
            'backup_cost_per_gb_server': float(plan[12]),
            'support_level': plan[13],
            'antivirus': plan[14],
            'soc': plan[15],
            'password_manager': plan[16],
            'sat': plan[17],
            'email_security': plan[18],
            'network_management': plan[19]
        }

        try:
            # Check if plan exists
            response = requests.get(
                f"{CODEX_URL}/api/billing-plans",
                params={'plan_name': plan_data['plan_name'], 'term_length': plan_data['term_length']},
                headers=headers,
                timeout=5
            )

            if response.status_code == 200 and response.json():
                # Plan exists, update it
                plan_id = response.json()[0]['id']
                response = requests.put(
                    f"{CODEX_URL}/api/billing-plans/{plan_id}",
                    json=plan_data,
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✓ Updated: {plan_data['plan_name']} ({plan_data['term_length']})")
                    imported_count += 1
                else:
                    print(f"✗ Failed to update: {plan_data['plan_name']} ({plan_data['term_length']})")
                    failed_count += 1
            else:
                # Plan doesn't exist, create it
                response = requests.post(
                    f"{CODEX_URL}/api/billing-plans",
                    json=plan_data,
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 201:
                    print(f"✓ Created: {plan_data['plan_name']} ({plan_data['term_length']})")
                    imported_count += 1
                else:
                    print(f"✗ Failed to create: {plan_data['plan_name']} ({plan_data['term_length']})")
                    print(f"   Error: {response.status_code} - {response.text}")
                    failed_count += 1

        except Exception as e:
            print(f"✗ Error processing {plan_data['plan_name']}: {e}")
            failed_count += 1

    return imported_count, failed_count


def import_features(features_data):
    """Import default features into Codex."""
    token = get_service_token("codex")
    if not token:
        print("ERROR: Could not get service token for Codex")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    imported_count = 0
    failed_count = 0

    for feature in features_data:
        if len(feature) < 2:
            print(f"WARNING: Skipping invalid feature data: {feature}")
            failed_count += 1
            continue

        feature_data = {
            'feature_type': feature[0],
            'value': feature[1]
        }

        try:
            # Check if feature exists
            response = requests.get(
                f"{CODEX_URL}/api/features",
                params={'feature_type': feature_data['feature_type'], 'value': feature_data['value']},
                headers=headers,
                timeout=5
            )

            if response.status_code == 200 and response.json():
                # Feature exists, skip
                print(f"  Exists: {feature_data['feature_type']}: {feature_data['value']}")
                imported_count += 1
            else:
                # Feature doesn't exist, create it
                response = requests.post(
                    f"{CODEX_URL}/api/features",
                    json=feature_data,
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 201:
                    print(f"✓ Created: {feature_data['feature_type']}: {feature_data['value']}")
                    imported_count += 1
                else:
                    print(f"✗ Failed to create: {feature_data['feature_type']}: {feature_data['value']}")
                    failed_count += 1

        except Exception as e:
            print(f"✗ Error processing feature {feature_data['feature_type']}: {e}")
            failed_count += 1

    return imported_count, failed_count


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  From file:  python import_billing_plans.py <json_file_path>")
        print("  From stdin: python import_billing_plans.py --stdin")
        print("\nExample: python import_billing_plans.py plans_config.json")
        sys.exit(1)

    # Load JSON from stdin or file
    config = None

    if sys.argv[1] == '--stdin':
        # Read from stdin
        try:
            print("Reading JSON from stdin...")
            json_data = sys.stdin.read()
            config = json.loads(json_data)
        except Exception as e:
            print(f"ERROR: Could not parse JSON from stdin: {e}")
            sys.exit(1)
    else:
        # Read from file
        json_file_path = sys.argv[1]

        # Check if file exists
        if not os.path.exists(json_file_path):
            print(f"ERROR: File not found: {json_file_path}")
            sys.exit(1)

        # Load JSON file
        try:
            with open(json_file_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"ERROR: Could not load JSON file: {e}")
            sys.exit(1)

    # Validate JSON structure
    if 'default_plans_data' not in config:
        print("ERROR: JSON file must contain 'default_plans_data' key")
        sys.exit(1)

    plans_data = config['default_plans_data']
    features_data = config.get('default_features', [])

    # Show summary
    print(f"\nLoaded configuration:")
    print(f"  Billing Plans: {len(plans_data)}")
    print(f"  Features: {len(features_data)}")
    print()

    # Request approval
    approval_details = {
        'Billing Plans': str(len(plans_data)),
        'Features': str(len(features_data)),
        'Action': 'Create/Update plans and features in Codex'
    }

    # Add source info
    if sys.argv[1] == '--stdin':
        approval_details['Source'] = 'Pasted JSON data'
    else:
        approval_details['Source'] = f'File: {sys.argv[1]}'

    approved = request_approval(
        f"Import {len(plans_data)} billing plans and {len(features_data)} features",
        approval_details
    )

    if not approved:
        print("✗ User denied the import")
        sys.exit(1)

    # Import features first
    if features_data:
        print("\n=== Importing Features ===")
        features_imported, features_failed = import_features(features_data)
        print(f"\nFeatures: {features_imported} imported, {features_failed} failed")

    # Import billing plans
    print("\n=== Importing Billing Plans ===")
    plans_imported, plans_failed = import_billing_plans(plans_data)

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    if features_data:
        print(f"Features: {features_imported} imported, {features_failed} failed")
    print(f"Billing Plans: {plans_imported} imported, {plans_failed} failed")
    print("=" * 70)

    if plans_failed > 0 or (features_data and features_failed > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
