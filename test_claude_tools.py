#!/usr/bin/env python3
"""
Test Claude Tools for Billing & Contract Management

Tests the tools that Claude Code will actually call.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from claude_tools import billing_tools, contract_tools

def test_billing_tools():
    """Test billing management tools."""
    print("="*70)
    print("Testing Billing Tools")
    print("="*70)

    # Test 1: Get billing plans
    print("\n1. Getting billing plans...")
    plans = billing_tools.get_billing_plans()
    if plans:
        print(f"✓ Found {len(plans)} billing plans")
        print(f"   Example: {plans[0]['billing_plan']} - {plans[0]['term_length']}")
    else:
        print("✗ Failed to get plans")

    # Test 2: Get dashboard
    print("\n2. Getting billing dashboard...")
    dashboard = billing_tools.get_all_companies_billing()
    if 'companies' in dashboard:
        companies = dashboard['companies']
        print(f"✓ Found {len(companies)} companies")
        if companies:
            test_company = companies[0]
            test_account = test_company['account_number']
            print(f"   Test company: {test_company['name']} ({test_account})")
            return test_account
    else:
        print("✗ Failed to get dashboard")

    return None

def test_billing_for_company(account_number):
    """Test getting billing for specific company."""
    print(f"\n3. Getting billing for {account_number}...")
    billing = billing_tools.get_billing_for_company(account_number)

    if 'error' in billing:
        print(f"✗ Error: {billing['error']}")
        return False

    if 'receipt' in billing:
        receipt = billing['receipt']
        print(f"✓ Company: {billing.get('company_name', 'N/A')}")
        print(f"   Total: ${receipt.get('total', 0):.2f}")
        print(f"   Users: {billing.get('quantities', {}).get('regular_users', 0)}")
        return True
    else:
        print("✗ No receipt in response")
        return False

def test_overrides(account_number):
    """Test override management."""
    print(f"\n4. Getting overrides for {account_number}...")
    overrides = billing_tools.get_company_overrides(account_number)

    if 'error' in overrides:
        print(f"✗ Error: {billing['error']}")
        return False

    if overrides.get('overrides'):
        print(f"✓ Company has custom overrides")
    else:
        print(f"✓ No custom overrides (using plan defaults)")

    return True

def test_contract_tools(account_number):
    """Test contract alignment tools."""
    print("\n" + "="*70)
    print("Testing Contract Tools")
    print("="*70)

    # Test 1: Get current settings
    print(f"\n1. Getting current settings for {account_number}...")
    settings = contract_tools.get_current_billing_settings(account_number)

    if 'error' in settings:
        print(f"✗ Error: {settings['error']}")
        return False

    if 'billing_data' in settings:
        print(f"✓ Retrieved comprehensive settings")
        print(f"   Billing data: {'data' in settings['billing_data']}")
        print(f"   Overrides: {settings.get('overrides') is not None}")
        print(f"   Plans available: {len(settings.get('available_plans', []))}")
    else:
        print("✗ Missing billing_data")
        return False

    # Test 2: Compare contract terms
    print(f"\n2. Comparing sample contract terms...")
    contract_terms = {
        "per_user_rate": 30.00,
        "hourly_rate": 150.00,
        "prepaid_hours_monthly": 4.0
    }

    comparison = contract_tools.compare_contract_terms(account_number, contract_terms)

    if 'error' in comparison:
        print(f"✗ Error: {comparison['error']}")
        return False

    discrepancies = comparison.get('discrepancies_found', 0)
    print(f"✓ Comparison complete")
    print(f"   Discrepancies found: {discrepancies}")
    if discrepancies > 0:
        print(f"   Recommendations:")
        for rec in comparison.get('recommendations', [])[:3]:
            print(f"     - {rec}")

    # Test 3: Dry run alignment
    print(f"\n3. Testing alignment (dry run)...")
    adjustments = {
        "per_user_cost": 30.00
    }

    result = contract_tools.align_billing_to_contract(
        account_number,
        adjustments,
        dry_run=True
    )

    if 'error' in result:
        print(f"✗ Error: {result['error']}")
        return False

    if result.get('dry_run'):
        print(f"✓ Dry run successful")
        print(f"   Would apply: {result.get('would_apply')}")
    else:
        print("✗ Not a dry run!")

    return True

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Claude Tools Test Suite")
    print("="*70)

    # Test billing tools
    test_account = test_billing_tools()

    if not test_account:
        print("\n⚠️  Could not get test account, using default")
        test_account = "620547"

    # Test billing for specific company
    test_billing_for_company(test_account)
    test_overrides(test_account)

    # Test contract tools
    test_contract_tools(test_account)

    print("\n" + "="*70)
    print("Tests Complete!")
    print("="*70)
    print("\nThese tools are now available for Claude Code to call.")
    print("Claude can use them to:")
    print("  - View billing information")
    print("  - Manage overrides and custom pricing")
    print("  - Parse contracts and align settings automatically")
    print()

if __name__ == "__main__":
    sys.exit(main())
