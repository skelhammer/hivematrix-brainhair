"""
Billing Management Tools

Tools for viewing and managing billing data through Ledger service.
Claude Code can call these to help with contract management and billing questions.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ledger_client import get_ledger_client

# Initialize client
ledger = get_ledger_client()


def get_billing_for_company(account_number: str, year: int = None, month: int = None) -> dict:
    """
    Get complete billing information for a company.

    Args:
        account_number: Company account number (e.g., "620547")
        year: Billing year (optional, defaults to current)
        month: Billing month 1-12 (optional, defaults to current)

    Returns:
        {
            "account_number": "620547",
            "company_name": "Acme Corp",
            "billing_period": "2025-10",
            "receipt": {
                "total": 5234.50,
                "total_user_charges": 1500.00,
                "total_asset_charges": 2250.00,
                "ticket_charge": 450.00,
                "backup_charge": 234.50,
                "billable_hours": 3.0,
                ...
            },
            "quantities": {
                "regular_users": 50,
                "workstation": 25,
                "server": 5,
                ...
            },
            "effective_rates": {
                "per_user_cost": 30.00,
                "per_workstation_cost": 90.00,
                ...
            }
        }

    Example:
        >>> billing = get_billing_for_company("620547")
        >>> print(f"Total bill: ${billing['receipt']['total']:.2f}")
        >>> print(f"Users: {billing['quantities']['regular_users']}")
    """
    try:
        return ledger.get_billing_for_client(account_number, year, month)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def get_all_companies_billing(year: int = None, month: int = None) -> dict:
    """
    Get billing dashboard for all companies.

    Args:
        year: Billing year (optional)
        month: Billing month (optional)

    Returns:
        {
            "billing_period": "2025-10",
            "companies": [
                {
                    "account_number": "620547",
                    "name": "Acme Corp",
                    "total_bill": 5234.50,
                    "workstations": 25,
                    "servers": 5,
                    "users": 50,
                    "hours": 3.5,
                    ...
                },
                ...
            ]
        }

    Example:
        >>> dashboard = get_all_companies_billing()
        >>> for company in dashboard['companies']:
        ...     print(f"{company['name']}: ${company['total_bill']:.2f}")
    """
    try:
        return ledger.get_billing_dashboard(year, month)
    except Exception as e:
        return {
            'error': str(e),
            'companies': []
        }


def get_billing_plans() -> list:
    """
    Get list of all available billing plans with rates.

    Returns:
        [
            {
                "id": 1,
                "billing_plan": "Premium Support",
                "term_length": "1-Year",
                "support_level": "All Inclusive",
                "per_user_cost": 30.00,
                "per_workstation_cost": 90.00,
                "per_server_cost": 150.00,
                ...
            },
            ...
        ]

    Example:
        >>> plans = get_billing_plans()
        >>> for plan in plans:
        ...     print(f"{plan['billing_plan']} - {plan['term_length']}")
    """
    try:
        return ledger.get_billing_plans()
    except Exception as e:
        return []


def get_company_overrides(account_number: str) -> dict:
    """
    Get billing overrides configured for a specific company.

    Args:
        account_number: Company account number

    Returns:
        {
            "overrides": {
                "billing_plan": "Custom Plan",  # or null if not overridden
                "per_user_cost": 25.00,  # or null
                "per_workstation_cost": 85.00,  # or null
                "prepaid_hours_monthly": 5.0,  # or null
                ...
            }
        }

    Example:
        >>> overrides = get_company_overrides("620547")
        >>> if overrides['overrides']:
        ...     print("Company has custom pricing")
    """
    try:
        return ledger.get_client_overrides(account_number)
    except Exception as e:
        return {
            'error': str(e),
            'overrides': None
        }


def set_billing_override(account_number: str, **overrides) -> dict:
    """
    Set or update billing overrides for a company.

    Args:
        account_number: Company account number
        **overrides: Override values (all optional):
            - billing_plan: str
            - support_level: str
            - per_user_cost: float
            - per_workstation_cost: float
            - per_server_cost: float
            - per_vm_cost: float
            - per_switch_cost: float
            - per_firewall_cost: float
            - per_hour_ticket_cost: float
            - prepaid_hours_monthly: float
            - prepaid_hours_yearly: float

    Returns:
        {
            "message": "Overrides updated successfully"
        }

    Example:
        >>> result = set_billing_override(
        ...     "620547",
        ...     per_user_cost=25.00,
        ...     prepaid_hours_monthly=5.0
        ... )
        >>> print(result['message'])
    """
    try:
        return ledger.set_client_override(account_number, overrides)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def add_manual_asset(
    account_number: str,
    hostname: str,
    billing_type: str,
    custom_cost: float = None,
    notes: str = None
) -> dict:
    """
    Add a manual asset that's not tracked in Codex/Datto.

    Args:
        account_number: Company account number
        hostname: Asset hostname/name
        billing_type: Type: "Workstation", "Server", "VM", "Switch", "Firewall", "Custom", "No Charge"
        custom_cost: Cost if billing_type is "Custom" (optional)
        notes: Additional notes (optional)

    Returns:
        {
            "message": "Manual asset added",
            "id": 123
        }

    Example:
        >>> result = add_manual_asset(
        ...     "620547",
        ...     "legacy-server-01",
        ...     "Server",
        ...     notes="Legacy server not in Datto"
        ... )
        >>> print(f"Added asset ID: {result['id']}")
    """
    try:
        return ledger.add_manual_asset(account_number, hostname, billing_type, custom_cost, notes)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def add_manual_user(
    account_number: str,
    full_name: str,
    billing_type: str = "Paid",
    custom_cost: float = None,
    notes: str = None
) -> dict:
    """
    Add a manual user that's not tracked in Codex/FreshService.

    Args:
        account_number: Company account number
        full_name: User's full name
        billing_type: "Paid", "Free", or "Custom"
        custom_cost: Cost if billing_type is "Custom" (optional)
        notes: Additional notes (optional)

    Returns:
        {
            "message": "Manual user added",
            "id": 456
        }

    Example:
        >>> result = add_manual_user(
        ...     "620547",
        ...     "John Executive",
        ...     billing_type="Paid",
        ...     notes="C-level executive"
        ... )
        >>> print(f"Added user ID: {result['id']}")
    """
    try:
        return ledger.add_manual_user(account_number, full_name, billing_type, custom_cost, notes)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def add_line_item(
    account_number: str,
    name: str,
    description: str = None,
    monthly_fee: float = None,
    one_off_fee: float = None,
    one_off_month: int = None,
    one_off_year: int = None,
    yearly_fee: float = None,
    yearly_bill_month: int = None
) -> dict:
    """
    Add a custom line item (recurring, one-time, or yearly charge).

    Args:
        account_number: Company account number
        name: Line item name
        description: Description (optional)
        monthly_fee: Recurring monthly amount (optional)
        one_off_fee: One-time charge amount (optional)
        one_off_month: Month for one-time charge 1-12 (required if one_off_fee)
        one_off_year: Year for one-time charge (required if one_off_fee)
        yearly_fee: Annual charge amount (optional)
        yearly_bill_month: Month to bill yearly 1-12 (required if yearly_fee)

    Returns:
        {
            "message": "Custom line item added",
            "id": 789
        }

    Examples:
        >>> # Recurring monthly charge
        >>> add_line_item("620547", "Office 365 Licenses", monthly_fee=500.00)

        >>> # One-time charge
        >>> add_line_item(
        ...     "620547",
        ...     "Server Migration",
        ...     one_off_fee=5000.00,
        ...     one_off_month=11,
        ...     one_off_year=2025
        ... )

        >>> # Annual charge
        >>> add_line_item(
        ...     "620547",
        ...     "Annual Security Audit",
        ...     yearly_fee=2500.00,
        ...     yearly_bill_month=1
        ... )
    """
    try:
        kwargs = {
            'name': name,
            'description': description,
            'monthly_fee': monthly_fee,
            'one_off_fee': one_off_fee,
            'one_off_month': one_off_month,
            'one_off_year': one_off_year,
            'yearly_fee': yearly_fee,
            'yearly_bill_month': yearly_bill_month
        }
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        return ledger.add_custom_line_item(account_number, **kwargs)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def get_invoice_summary(account_number: str, year: int, month: int) -> dict:
    """
    Get invoice summary for a specific billing period.

    Args:
        account_number: Company account number
        year: Invoice year
        month: Invoice month 1-12

    Returns:
        {
            "invoice_number": "620547-2025-10",
            "company_name": "Acme Corp",
            "total": 5234.50,
            "is_archived": false,
            ...
        }

    Example:
        >>> summary = get_invoice_summary("620547", 2025, 10)
        >>> print(f"Invoice: {summary['invoice_number']}")
        >>> print(f"Total: ${summary['total']:.2f}")
        >>> if summary['is_archived']:
        ...     print("Already finalized")
    """
    try:
        return ledger.get_invoice_summary(account_number, year, month)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }
