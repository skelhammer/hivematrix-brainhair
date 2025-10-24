"""
Contract Alignment Tool

This module provides tools for Claude Code to analyze contracts and align Ledger
billing settings to match contract terms.
"""

from .ledger_client import get_ledger_client
from .helm_logger import get_helm_logger
from typing import Dict, List, Any, Optional
import re


class ContractAlignmentTool:
    """
    Tool for analyzing contracts and aligning billing settings.

    This class provides methods that Claude Code can call to:
    1. Extract billing information from contract text
    2. Compare contract terms with current billing settings
    3. Apply changes to align settings with contract
    4. Generate alignment reports
    """

    def __init__(self):
        self.ledger = get_ledger_client()
        self.logger = get_helm_logger()

    def analyze_contract(self, contract_text: str, account_number: str) -> Dict:
        """
        Analyze a contract and extract billing-related information.

        This is a helper method for Claude Code. Claude should parse the contract
        using its natural language understanding and provide structured data.

        Args:
            contract_text: Full contract text or relevant excerpts
            account_number: Company account number

        Returns:
            Dict with extracted information and recommendations
        """
        self.logger.info(f"Analyzing contract for account {account_number}")

        # Get current billing settings
        current_billing = self.ledger.get_billing_for_client(account_number)
        current_overrides = self.ledger.get_client_overrides(account_number)

        return {
            'account_number': account_number,
            'current_billing': current_billing,
            'current_overrides': current_overrides,
            'contract_excerpt': contract_text[:500] if len(contract_text) > 500 else contract_text,
            'message': 'Contract loaded. Use Claude Code to parse billing terms and call alignment functions.'
        }

    def get_current_settings(self, account_number: str) -> Dict:
        """
        Get current billing settings for a company.

        Args:
            account_number: Company account number

        Returns:
            Current billing configuration
        """
        self.logger.info(f"Fetching current settings for {account_number}")

        billing_data = self.ledger.get_billing_for_client(account_number)
        overrides = self.ledger.get_client_overrides(account_number)
        plans = self.ledger.get_billing_plans()
        manual_assets = self.ledger.get_manual_assets(account_number)
        manual_users = self.ledger.get_manual_users(account_number)
        line_items = self.ledger.get_custom_line_items(account_number)

        return {
            'account_number': account_number,
            'billing_data': billing_data,
            'overrides': overrides,
            'available_plans': plans,
            'manual_assets': manual_assets,
            'manual_users': manual_users,
            'line_items': line_items
        }

    def compare_contract_to_settings(self,
                                     account_number: str,
                                     contract_terms: Dict) -> Dict:
        """
        Compare extracted contract terms with current billing settings.

        Args:
            account_number: Company account number
            contract_terms: Dict with extracted contract terms
                Example:
                {
                    "billing_method": "per_user" or "flat_fee" or "per_device",
                    "per_user_rate": 15.00,
                    "flat_fee_amount": 5000.00,
                    "included_users": 50,
                    "included_workstations": 25,
                    "included_servers": 5,
                    "hourly_rate": 150.00,
                    "prepaid_hours_monthly": 4.0,
                    "support_level": "All Inclusive",
                    "custom_items": [...]
                }

        Returns:
            Comparison report with discrepancies
        """
        self.logger.info(f"Comparing contract terms for {account_number}")

        current = self.get_current_settings(account_number)

        discrepancies = []
        recommendations = []

        # Extract current effective rates
        current_billing = current.get('billing_data', {}).get('data', {})
        effective_rates = current_billing.get('effective_rates', {})
        receipt = current_billing.get('receipt', {})

        # Compare per-user rate
        if 'per_user_rate' in contract_terms:
            contract_rate = float(contract_terms['per_user_rate'])
            current_rate = float(effective_rates.get('per_user_cost', 0))

            if abs(contract_rate - current_rate) > 0.01:
                discrepancies.append({
                    'field': 'per_user_cost',
                    'contract_value': contract_rate,
                    'current_value': current_rate,
                    'difference': contract_rate - current_rate
                })
                recommendations.append(f"Set per_user_cost to ${contract_rate}")

        # Compare hourly rate
        if 'hourly_rate' in contract_terms:
            contract_rate = float(contract_terms['hourly_rate'])
            current_rate = float(effective_rates.get('per_hour_ticket_cost', 0))

            if abs(contract_rate - current_rate) > 0.01:
                discrepancies.append({
                    'field': 'per_hour_ticket_cost',
                    'contract_value': contract_rate,
                    'current_value': current_rate,
                    'difference': contract_rate - current_rate
                })
                recommendations.append(f"Set per_hour_ticket_cost to ${contract_rate}")

        # Compare prepaid hours
        if 'prepaid_hours_monthly' in contract_terms:
            contract_hours = float(contract_terms['prepaid_hours_monthly'])
            overrides = current.get('overrides', {}).get('overrides', {})
            current_hours = float(overrides.get('prepaid_hours_monthly', 0) if overrides else 0)

            if abs(contract_hours - current_hours) > 0.01:
                discrepancies.append({
                    'field': 'prepaid_hours_monthly',
                    'contract_value': contract_hours,
                    'current_value': current_hours,
                    'difference': contract_hours - current_hours
                })
                recommendations.append(f"Set prepaid_hours_monthly to {contract_hours}")

        # Check for flat fee
        if contract_terms.get('billing_method') == 'flat_fee':
            flat_fee = float(contract_terms.get('flat_fee_amount', 0))
            current_total = float(receipt.get('total', 0))

            if abs(flat_fee - current_total) > 0.01:
                discrepancies.append({
                    'field': 'total_bill',
                    'contract_value': flat_fee,
                    'current_value': current_total,
                    'difference': flat_fee - current_total,
                    'note': 'Flat fee contract - may need custom line item adjustments'
                })
                recommendations.append(
                    f"Contract specifies flat fee of ${flat_fee}. Current bill is ${current_total}. "
                    f"Consider adding custom line item to adjust total."
                )

        # Check support level
        if 'support_level' in contract_terms:
            contract_level = contract_terms['support_level']
            current_level = effective_rates.get('support_level', '')

            if contract_level != current_level:
                discrepancies.append({
                    'field': 'support_level',
                    'contract_value': contract_level,
                    'current_value': current_level
                })
                recommendations.append(f"Set support_level to '{contract_level}'")

        return {
            'account_number': account_number,
            'discrepancies_found': len(discrepancies),
            'discrepancies': discrepancies,
            'recommendations': recommendations,
            'alignment_needed': len(discrepancies) > 0
        }

    def align_settings(self,
                      account_number: str,
                      adjustments: Dict,
                      dry_run: bool = True) -> Dict:
        """
        Apply adjustments to align billing settings with contract.

        Args:
            account_number: Company account number
            adjustments: Dict with fields to adjust
                Example:
                {
                    "per_user_cost": 15.00,
                    "per_hour_ticket_cost": 150.00,
                    "prepaid_hours_monthly": 4.0,
                    "support_level": "All Inclusive",
                    "add_line_items": [
                        {
                            "name": "Flat Fee Adjustment",
                            "monthly_fee": 1000.00
                        }
                    ]
                }
            dry_run: If True, don't actually apply changes (default True)

        Returns:
            Result of alignment operation
        """
        self.logger.info(f"Aligning settings for {account_number} (dry_run={dry_run})")

        if dry_run:
            return {
                'account_number': account_number,
                'dry_run': True,
                'would_apply': adjustments,
                'message': 'Dry run - no changes made. Set dry_run=False to apply.'
            }

        results = []
        errors = []

        # Apply overrides
        override_fields = {}
        for field in ['per_user_cost', 'per_workstation_cost', 'per_server_cost', 'per_vm_cost',
                     'per_switch_cost', 'per_firewall_cost', 'per_hour_ticket_cost',
                     'prepaid_hours_monthly', 'prepaid_hours_yearly', 'support_level', 'billing_plan']:
            if field in adjustments:
                override_fields[field] = adjustments[field]

        if override_fields:
            result = self.ledger.set_client_override(account_number, override_fields)
            if 'error' in result:
                errors.append(f"Error setting overrides: {result['error']}")
            else:
                results.append(f"Applied {len(override_fields)} override(s)")

        # Add line items
        if 'add_line_items' in adjustments:
            for item in adjustments['add_line_items']:
                result = self.ledger.add_custom_line_item(account_number, **item)
                if 'error' in result:
                    errors.append(f"Error adding line item '{item.get('name')}': {result['error']}")
                else:
                    results.append(f"Added line item: {item.get('name')}")

        # Add manual assets
        if 'add_manual_assets' in adjustments:
            for asset in adjustments['add_manual_assets']:
                result = self.ledger.add_manual_asset(
                    account_number,
                    asset['hostname'],
                    asset['billing_type'],
                    asset.get('custom_cost'),
                    asset.get('notes')
                )
                if 'error' in result:
                    errors.append(f"Error adding asset '{asset['hostname']}': {result['error']}")
                else:
                    results.append(f"Added manual asset: {asset['hostname']}")

        # Add manual users
        if 'add_manual_users' in adjustments:
            for user in adjustments['add_manual_users']:
                result = self.ledger.add_manual_user(
                    account_number,
                    user['full_name'],
                    user['billing_type'],
                    user.get('custom_cost'),
                    user.get('notes')
                )
                if 'error' in result:
                    errors.append(f"Error adding user '{user['full_name']}': {result['error']}")
                else:
                    results.append(f"Added manual user: {user['full_name']}")

        return {
            'account_number': account_number,
            'dry_run': False,
            'changes_applied': len(results),
            'results': results,
            'errors': errors,
            'success': len(errors) == 0
        }

    def verify_alignment(self, account_number: str, contract_terms: Dict) -> Dict:
        """
        Verify that billing settings now match contract terms.

        Args:
            account_number: Company account number
            contract_terms: Expected contract terms

        Returns:
            Verification report
        """
        self.logger.info(f"Verifying alignment for {account_number}")

        comparison = self.compare_contract_to_settings(account_number, contract_terms)

        if comparison['alignment_needed']:
            return {
                'aligned': False,
                'remaining_discrepancies': comparison['discrepancies_found'],
                'details': comparison
            }
        else:
            return {
                'aligned': True,
                'message': 'Billing settings match contract terms',
                'details': comparison
            }


# Global instance
_contract_tool = None

def get_contract_alignment_tool() -> ContractAlignmentTool:
    """Get the global ContractAlignmentTool instance."""
    global _contract_tool
    if _contract_tool is None:
        _contract_tool = ContractAlignmentTool()
    return _contract_tool
