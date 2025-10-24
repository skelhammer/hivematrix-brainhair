#!/usr/bin/env python3
"""
Test Ledger-Brainhair Integration

Tests all the new billing management and contract alignment tools.
Uses service tokens from Core for authentication.
"""

import sys
import json
import requests
from datetime import datetime

# Service URLs
CORE_URL = "http://localhost:5000"
LEDGER_URL = "http://localhost:5030"
CODEX_URL = "http://localhost:5010"
BRAINHAIR_URL = "http://localhost:5050"

# Test tracking
tests_passed = 0
tests_failed = 0

def print_header(text):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_test(name, passed, details=""):
    """Print test result."""
    global tests_passed, tests_failed

    status = "✓ PASS" if passed else "✗ FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"

    print(f"{color}{status}{reset} - {name}")
    if details:
        print(f"       {details}")

    if passed:
        tests_passed += 1
    else:
        tests_failed += 1

def get_service_token(calling_service, target_service):
    """Get a service token from Core."""
    try:
        response = requests.post(
            f"{CORE_URL}/service-token",
            json={
                "calling_service": calling_service,
                "target_service": target_service
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["token"]
        else:
            print(f"Failed to get token: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def test_ledger_direct():
    """Test Ledger API directly."""
    print_header("Testing Ledger API (Direct)")

    token = get_service_token("test", "ledger")
    if not token:
        print_test("Get service token for Ledger", False, "Could not get token")
        return None

    print_test("Get service token for Ledger", True)
    headers = {"Authorization": f"Bearer {token}"}

    # Test billing plans
    try:
        response = requests.get(f"{LEDGER_URL}/api/plans", headers=headers, timeout=5)
        if response.status_code == 200:
            plans = response.json()
            print_test("Get billing plans", True, f"Found {len(plans)} plans")
        else:
            print_test("Get billing plans", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get billing plans", False, str(e))

    # Test billing dashboard
    try:
        response = requests.get(f"{LEDGER_URL}/api/billing/dashboard", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            companies = data.get("companies", [])
            print_test("Get billing dashboard", True, f"Found {len(companies)} companies")
            if companies:
                return companies[0]["account_number"]  # Return test account
        else:
            print_test("Get billing dashboard", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get billing dashboard", False, str(e))

    return None

def test_ledger_via_brainhair(account_number):
    """Test Ledger access through Brainhair proxy."""
    print_header("Testing Ledger via Brainhair Proxy")

    token = get_service_token("test", "brainhair")
    if not token:
        print_test("Get service token for Brainhair", False)
        return

    print_test("Get service token for Brainhair", True)
    headers = {"Authorization": f"Bearer {token}"}

    # Test billing data endpoint
    try:
        response = requests.get(
            f"{BRAINHAIR_URL}/api/ledger/billing/{account_number}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            billing_data = data.get("data", {})
            print_test("Get billing data via Brainhair", True,
                      f"Account: {billing_data.get('company_name', 'N/A')}")
        else:
            print_test("Get billing data via Brainhair", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get billing data via Brainhair", False, str(e))

    # Test plans endpoint
    try:
        response = requests.get(
            f"{BRAINHAIR_URL}/api/ledger/plans",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            plans = data.get("plans", [])
            print_test("Get plans via Brainhair", True, f"Found {len(plans)} plans")
        else:
            print_test("Get plans via Brainhair", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get plans via Brainhair", False, str(e))

    # Test client overrides
    try:
        response = requests.get(
            f"{BRAINHAIR_URL}/api/ledger/overrides/client/{account_number}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print_test("Get client overrides via Brainhair", True)
        else:
            print_test("Get client overrides via Brainhair", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get client overrides via Brainhair", False, str(e))

def test_override_management(account_number):
    """Test client override management."""
    print_header("Testing Override Management")

    token = get_service_token("test", "brainhair")
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test setting overrides (dry run style - we'll delete right after)
    test_override = {
        "per_user_cost": 99.99,
        "prepaid_hours_monthly": 10.0
    }

    try:
        response = requests.put(
            f"{BRAINHAIR_URL}/api/ledger/overrides/client/{account_number}",
            headers=headers,
            json=test_override,
            timeout=5
        )
        if response.status_code == 200:
            print_test("Set client override", True, "Applied test override")

            # Verify it was set
            response = requests.get(
                f"{BRAINHAIR_URL}/api/ledger/overrides/client/{account_number}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                overrides = data.get("overrides", {})
                if overrides and overrides.get("per_user_cost") == 99.99:
                    print_test("Verify override was set", True)
                else:
                    print_test("Verify override was set", False, "Override not found")

            # Clean up - delete the override
            response = requests.delete(
                f"{BRAINHAIR_URL}/api/ledger/overrides/client/{account_number}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                print_test("Delete client override", True, "Cleaned up test override")
            else:
                print_test("Delete client override", False, f"HTTP {response.status_code}")
        else:
            print_test("Set client override", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Override management", False, str(e))

def test_manual_assets(account_number):
    """Test manual asset management."""
    print_header("Testing Manual Asset Management")

    token = get_service_token("test", "brainhair")
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Add a test manual asset
    test_asset = {
        "hostname": "test-server-999",
        "billing_type": "Server",
        "custom_cost": 150.00,
        "notes": "Test asset - delete me"
    }

    try:
        response = requests.post(
            f"{BRAINHAIR_URL}/api/ledger/manual-assets/{account_number}",
            headers=headers,
            json=test_asset,
            timeout=5
        )
        if response.status_code in [200, 201]:
            data = response.json()
            asset_id = data.get("id")
            print_test("Add manual asset", True, f"Created asset ID {asset_id}")

            # Verify it appears in the list
            response = requests.get(
                f"{BRAINHAIR_URL}/api/ledger/manual-assets/{account_number}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                assets = data.get("manual_assets", [])
                found = any(a.get("hostname") == "test-server-999" for a in assets)
                if found:
                    print_test("Verify manual asset in list", True)
                else:
                    print_test("Verify manual asset in list", False, "Asset not found in list")

            # Clean up - delete the asset
            if asset_id:
                response = requests.delete(
                    f"{BRAINHAIR_URL}/api/ledger/manual-assets/{account_number}/{asset_id}",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    print_test("Delete manual asset", True, "Cleaned up test asset")
                else:
                    print_test("Delete manual asset", False, f"HTTP {response.status_code}")
        else:
            print_test("Add manual asset", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print_test("Manual asset management", False, str(e))

def test_contract_alignment(account_number):
    """Test contract alignment tool."""
    print_header("Testing Contract Alignment Tool")

    token = get_service_token("test", "brainhair")
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get current settings
    try:
        response = requests.get(
            f"{BRAINHAIR_URL}/api/contract/current-settings/{account_number}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if "billing_data" in data:
                print_test("Get current settings", True, "Retrieved comprehensive settings")
            else:
                print_test("Get current settings", False, "Missing billing_data")
        else:
            print_test("Get current settings", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Get current settings", False, str(e))

    # Test contract comparison
    contract_terms = {
        "per_user_rate": 15.00,
        "hourly_rate": 150.00,
        "prepaid_hours_monthly": 4.0
    }

    try:
        response = requests.post(
            f"{BRAINHAIR_URL}/api/contract/compare",
            headers=headers,
            json={
                "account_number": account_number,
                "contract_terms": contract_terms
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            discrepancies = data.get("discrepancies_found", 0)
            print_test("Compare contract terms", True,
                      f"Found {discrepancies} discrepancies")
        else:
            print_test("Compare contract terms", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Compare contract terms", False, str(e))

    # Test alignment (dry run)
    try:
        response = requests.post(
            f"{BRAINHAIR_URL}/api/contract/align",
            headers=headers,
            json={
                "account_number": account_number,
                "adjustments": {
                    "per_user_cost": 15.00
                },
                "dry_run": True
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("dry_run") == True:
                print_test("Align settings (dry run)", True, "Dry run completed")
            else:
                print_test("Align settings (dry run)", False, "Not a dry run")
        else:
            print_test("Align settings (dry run)", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_test("Align settings (dry run)", False, str(e))

def print_summary():
    """Print test summary."""
    print_header("Test Summary")

    total = tests_passed + tests_failed
    percentage = (tests_passed / total * 100) if total > 0 else 0

    print(f"Total tests: {total}")
    print(f"Passed: \033[92m{tests_passed}\033[0m")
    print(f"Failed: \033[91m{tests_failed}\033[0m")
    print(f"Success rate: {percentage:.1f}%\n")

    return tests_failed == 0

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  Ledger-Brainhair Integration Test Suite")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    # Get a test account number
    account_number = test_ledger_direct()
    if not account_number:
        print("\n⚠️  Could not get test account number, using default")
        account_number = "620547"

    print(f"\n Using test account: {account_number}")

    # Run tests
    test_ledger_via_brainhair(account_number)
    test_override_management(account_number)
    test_manual_assets(account_number)
    test_contract_alignment(account_number)

    # Summary
    success = print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
