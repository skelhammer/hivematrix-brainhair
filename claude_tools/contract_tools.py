"""
Contract Alignment Tools

Tools for analyzing contracts and aligning billing settings to match contract terms.
Claude Code can parse contracts and use these to automatically configure billing.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.contract_alignment import get_contract_alignment_tool

# Initialize tool
tool = get_contract_alignment_tool()


def analyze_contract_for_company(contract_text: str, account_number: str) -> dict:
    """
    Load contract text and current billing settings for analysis.

    This is the starting point - Claude should:
    1. Call this to load current settings
    2. Parse the contract_text using natural language understanding
    3. Extract billing terms
    4. Use compare_contract_terms() to find discrepancies
    5. Use align_billing_to_contract() to fix them

    Args:
        contract_text: Full contract text or billing-relevant excerpts
        account_number: Company account number

    Returns:
        {
            "account_number": "620547",
            "current_billing": {...},
            "current_overrides": {...},
            "contract_excerpt": "...",
            "message": "Contract loaded. Parse terms and call alignment functions."
        }

    Example:
        >>> contract = '''
        ... SERVICE AGREEMENT
        ...
        ... Client shall pay $30 per user per month.
        ... Support hours billed at $150/hour.
        ... Includes 4 hours prepaid support monthly.
        ... '''
        >>>
        >>> analysis = analyze_contract_for_company(contract, "620547")
        >>> # Now Claude parses the contract and extracts:
        >>> # - per_user_rate: 30.00
        >>> # - hourly_rate: 150.00
        >>> # - prepaid_hours_monthly: 4.0
    """
    try:
        return tool.analyze_contract(contract_text, account_number)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def get_current_billing_settings(account_number: str) -> dict:
    """
    Get comprehensive current billing configuration for a company.

    Args:
        account_number: Company account number

    Returns:
        {
            "account_number": "620547",
            "billing_data": {...},  # Current billing with receipts
            "overrides": {...},  # Custom rates if any
            "available_plans": [...],  # All available billing plans
            "manual_assets": [...],  # Manually added assets
            "manual_users": [...],  # Manually added users
            "line_items": [...]  # Custom line items
        }

    Example:
        >>> settings = get_current_billing_settings("620547")
        >>> current_rate = settings['billing_data']['effective_rates']['per_user_cost']
        >>> print(f"Current per-user rate: ${current_rate}")
    """
    try:
        return tool.get_current_settings(account_number)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def compare_contract_terms(account_number: str, contract_terms: dict) -> dict:
    """
    Compare extracted contract terms with current billing settings.

    After parsing a contract, Claude should extract the billing terms
    and pass them to this function to find discrepancies.

    Args:
        account_number: Company account number
        contract_terms: Dict with extracted terms:
            - billing_method: "per_user", "flat_fee", or "per_device"
            - per_user_rate: float (if applicable)
            - flat_fee_amount: float (if applicable)
            - hourly_rate: float
            - prepaid_hours_monthly: float
            - prepaid_hours_yearly: float
            - support_level: str
            - included_users: int (if flat fee with user cap)
            - included_workstations: int (if flat fee with device cap)
            - custom_items: list of dicts (if any special charges)

    Returns:
        {
            "account_number": "620547",
            "discrepancies_found": 3,
            "discrepancies": [
                {
                    "field": "per_user_cost",
                    "contract_value": 30.00,
                    "current_value": 25.00,
                    "difference": 5.00
                },
                ...
            ],
            "recommendations": [
                "Set per_user_cost to $30.00",
                "Set prepaid_hours_monthly to 4.0",
                ...
            ],
            "alignment_needed": true
        }

    Example:
        >>> # Claude parsed contract and extracted:
        >>> terms = {
        ...     "billing_method": "per_user",
        ...     "per_user_rate": 30.00,
        ...     "hourly_rate": 150.00,
        ...     "prepaid_hours_monthly": 4.0,
        ...     "support_level": "All Inclusive"
        ... }
        >>>
        >>> comparison = compare_contract_terms("620547", terms)
        >>> if comparison['alignment_needed']:
        ...     print(f"Found {comparison['discrepancies_found']} issues")
        ...     for rec in comparison['recommendations']:
        ...         print(f"  - {rec}")
    """
    try:
        return tool.compare_contract_to_settings(account_number, contract_terms)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def align_billing_to_contract(
    account_number: str,
    adjustments: dict,
    dry_run: bool = True
) -> dict:
    """
    Apply adjustments to align billing with contract terms.

    IMPORTANT: Always do a dry_run=True first to preview changes!

    Args:
        account_number: Company account number
        adjustments: Dict with fields to adjust:
            - per_user_cost: float
            - per_workstation_cost: float
            - per_server_cost: float
            - per_vm_cost: float
            - per_switch_cost: float
            - per_firewall_cost: float
            - per_hour_ticket_cost: float
            - prepaid_hours_monthly: float
            - prepaid_hours_yearly: float
            - support_level: str
            - billing_plan: str
            - add_line_items: list of dicts
            - add_manual_assets: list of dicts
            - add_manual_users: list of dicts
        dry_run: If True, don't actually apply (default: True for safety)

    Returns:
        {
            "account_number": "620547",
            "dry_run": true,
            "would_apply": {...},  # If dry_run
            "changes_applied": 5,  # If not dry_run
            "results": [...],
            "errors": [],
            "success": true
        }

    Examples:
        >>> # First, do a dry run to preview
        >>> result = align_billing_to_contract(
        ...     "620547",
        ...     {
        ...         "per_user_cost": 30.00,
        ...         "prepaid_hours_monthly": 4.0,
        ...         "support_level": "All Inclusive"
        ...     },
        ...     dry_run=True
        ... )
        >>> print("Would apply:", result['would_apply'])
        >>>
        >>> # If user approves, apply for real
        >>> result = align_billing_to_contract(
        ...     "620547",
        ...     {
        ...         "per_user_cost": 30.00,
        ...         "prepaid_hours_monthly": 4.0
        ...     },
        ...     dry_run=False
        ... )
        >>> print(f"Applied {result['changes_applied']} changes")

        >>> # Add flat fee adjustment
        >>> result = align_billing_to_contract(
        ...     "620547",
        ...     {
        ...         "add_line_items": [
        ...             {
        ...                 "name": "Flat Fee Base",
        ...                 "monthly_fee": 5000.00,
        ...                 "description": "Monthly flat fee per contract"
        ...             }
        ...         ]
        ...     },
        ...     dry_run=False
        ... )
    """
    try:
        return tool.align_settings(account_number, adjustments, dry_run)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number,
            'dry_run': dry_run
        }


def verify_contract_alignment(account_number: str, contract_terms: dict) -> dict:
    """
    Verify that billing settings now match contract terms.

    Call this after alignment to confirm everything matches.

    Args:
        account_number: Company account number
        contract_terms: Expected contract terms (same format as compare_contract_terms)

    Returns:
        {
            "aligned": true,
            "message": "Billing settings match contract terms"
        }
        OR
        {
            "aligned": false,
            "remaining_discrepancies": 2,
            "details": {...}
        }

    Example:
        >>> # After alignment, verify
        >>> terms = {
        ...     "per_user_rate": 30.00,
        ...     "prepaid_hours_monthly": 4.0
        ... }
        >>>
        >>> verification = verify_contract_alignment("620547", terms)
        >>> if verification['aligned']:
        ...     print("✓ Billing matches contract!")
        ... else:
        ...     print(f"✗ Still {verification['remaining_discrepancies']} issues")
    """
    try:
        return tool.verify_alignment(account_number, contract_terms)
    except Exception as e:
        return {
            'error': str(e),
            'account_number': account_number
        }


def workflow_example():
    """
    Example workflow for contract alignment.

    This is just documentation showing how Claude should use these tools.
    """
    example = '''
    # Complete Contract Alignment Workflow

    ## Step 1: Paste Contract
    User pastes contract text into Claude.

    ## Step 2: Load Current Settings
    >>> analysis = analyze_contract_for_company(contract_text, "620547")
    >>> current_settings = get_current_billing_settings("620547")

    ## Step 3: Parse Contract (Claude's NLU)
    Claude reads the contract and extracts:
    - Billing method (per-user, flat fee, etc.)
    - Rates (per user, hourly, etc.)
    - Included hours/resources
    - Special terms

    Example extraction:
    >>> contract_terms = {
    ...     "billing_method": "per_user",
    ...     "per_user_rate": 30.00,
    ...     "hourly_rate": 150.00,
    ...     "prepaid_hours_monthly": 4.0,
    ...     "support_level": "All Inclusive"
    ... }

    ## Step 4: Compare
    >>> comparison = compare_contract_terms("620547", contract_terms)
    >>> if comparison['discrepancies_found'] > 0:
    ...     print("Discrepancies found:")
    ...     for rec in comparison['recommendations']:
    ...         print(f"  - {rec}")

    ## Step 5: Prepare Adjustments
    >>> adjustments = {
    ...     "per_user_cost": 30.00,
    ...     "per_hour_ticket_cost": 150.00,
    ...     "prepaid_hours_monthly": 4.0,
    ...     "support_level": "All Inclusive"
    ... }

    ## Step 6: Dry Run
    >>> result = align_billing_to_contract("620547", adjustments, dry_run=True)
    >>> # Show user what would change

    ## Step 7: Apply (if user approves)
    >>> result = align_billing_to_contract("620547", adjustments, dry_run=False)
    >>> print(f"Applied {result['changes_applied']} changes")

    ## Step 8: Verify
    >>> verification = verify_contract_alignment("620547", contract_terms)
    >>> if verification['aligned']:
    ...     print("✓ Success! Billing now matches contract.")
    ... else:
    ...     print("Still some issues - investigating...")
    '''
    return example


# Export workflow documentation
__doc__ += "\n\n" + workflow_example()
