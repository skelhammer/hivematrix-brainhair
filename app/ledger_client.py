"""
Ledger Service Client

This module provides a client for interacting with the Ledger billing service.
Used by Brainhair to manage billing overrides and settings.
"""

from .service_client import call_service
from .helm_logger import get_helm_logger
from typing import Dict, List, Any, Optional
import json


class LedgerClient:
    """Client for interacting with Ledger billing service."""

    def __init__(self):
        self.logger = get_helm_logger()

    def _call_ledger(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Internal method to call Ledger service.

        Args:
            endpoint: API endpoint (e.g., '/api/billing/123456')
            method: HTTP method
            data: Request payload for POST/PUT

        Returns:
            Response data as dict
        """
        try:
            if method == 'GET':
                response = call_service('ledger', endpoint)
            elif method in ['POST', 'PUT']:
                response = call_service('ledger', endpoint, method=method, json=data)
            elif method == 'DELETE':
                response = call_service('ledger', endpoint, method='DELETE')
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code >= 200 and response.status_code < 300:
                return response.json()
            else:
                self.logger.error(f"Ledger API error: {response.status_code} - {response.text}")
                return {'error': f"Ledger returned {response.status_code}", 'details': response.text}

        except Exception as e:
            self.logger.error(f"Error calling Ledger: {e}", exc_info=True)
            return {'error': 'Internal server error'}

    # ===== BILLING DATA =====

    def get_billing_for_client(self, account_number: str, year: int = None, month: int = None) -> Dict:
        """
        Get billing data for a specific client.

        Args:
            account_number: Company account number
            year: Billing year (optional, defaults to current)
            month: Billing month (optional, defaults to current)

        Returns:
            Billing data including receipt, quantities, rates
        """
        endpoint = f'/api/billing/{account_number}'
        params = []
        if year:
            params.append(f'year={year}')
        if month:
            params.append(f'month={month}')
        if params:
            endpoint += '?' + '&'.join(params)

        self.logger.info(f"Fetching billing data for {account_number}")
        return self._call_ledger(endpoint)

    def get_billing_dashboard(self, year: int = None, month: int = None) -> Dict:
        """
        Get billing dashboard data for all companies.

        Args:
            year: Billing year (optional)
            month: Billing month (optional)

        Returns:
            Dashboard data with all companies
        """
        endpoint = '/api/billing/dashboard'
        params = []
        if year:
            params.append(f'year={year}')
        if month:
            params.append(f'month={month}')
        if params:
            endpoint += '?' + '&'.join(params)

        self.logger.info("Fetching billing dashboard")
        return self._call_ledger(endpoint)

    def get_billing_plans(self) -> List[Dict]:
        """
        Get list of all available billing plans.

        Returns:
            List of billing plans with rates
        """
        self.logger.info("Fetching billing plans")
        result = self._call_ledger('/api/plans')
        return result if isinstance(result, list) else []

    # ===== CLIENT OVERRIDES =====

    def get_client_overrides(self, account_number: str) -> Dict:
        """
        Get billing overrides for a specific client.

        Args:
            account_number: Company account number

        Returns:
            Override data or None
        """
        self.logger.info(f"Fetching overrides for {account_number}")
        return self._call_ledger(f'/api/overrides/client/{account_number}')

    def set_client_override(self, account_number: str, overrides: Dict) -> Dict:
        """
        Set or update billing overrides for a client.

        Args:
            account_number: Company account number
            overrides: Dict with override fields (billing_plan, per_user_cost, etc.)

        Returns:
            Success/error message
        """
        self.logger.info(f"Setting overrides for {account_number}: {list(overrides.keys())}")
        return self._call_ledger(f'/api/overrides/client/{account_number}', method='PUT', data=overrides)

    def delete_client_overrides(self, account_number: str) -> Dict:
        """
        Remove all billing overrides for a client.

        Args:
            account_number: Company account number

        Returns:
            Success message
        """
        self.logger.info(f"Deleting overrides for {account_number}")
        return self._call_ledger(f'/api/overrides/client/{account_number}', method='DELETE')

    # ===== ASSET OVERRIDES =====

    def get_asset_override(self, asset_id: int) -> Dict:
        """Get billing override for a specific asset."""
        return self._call_ledger(f'/api/overrides/asset/{asset_id}')

    def set_asset_override(self, asset_id: int, billing_type: str, custom_cost: float = None) -> Dict:
        """Set billing override for an asset."""
        data = {'billing_type': billing_type}
        if custom_cost is not None:
            data['custom_cost'] = custom_cost
        return self._call_ledger(f'/api/overrides/asset/{asset_id}', method='PUT', data=data)

    def delete_asset_override(self, asset_id: int) -> Dict:
        """Remove billing override for an asset."""
        return self._call_ledger(f'/api/overrides/asset/{asset_id}', method='DELETE')

    # ===== USER OVERRIDES =====

    def get_user_override(self, user_id: int) -> Dict:
        """Get billing override for a specific user."""
        return self._call_ledger(f'/api/overrides/user/{user_id}')

    def set_user_override(self, user_id: int, billing_type: str, custom_cost: float = None) -> Dict:
        """Set billing override for a user."""
        data = {'billing_type': billing_type}
        if custom_cost is not None:
            data['custom_cost'] = custom_cost
        return self._call_ledger(f'/api/overrides/user/{user_id}', method='PUT', data=data)

    def delete_user_override(self, user_id: int) -> Dict:
        """Remove billing override for a user."""
        return self._call_ledger(f'/api/overrides/user/{user_id}', method='DELETE')

    # ===== MANUAL ASSETS =====

    def get_manual_assets(self, account_number: str) -> List[Dict]:
        """Get all manual assets for a company."""
        result = self._call_ledger(f'/api/overrides/manual-assets/{account_number}')
        return result.get('manual_assets', []) if isinstance(result, dict) else []

    def add_manual_asset(self, account_number: str, hostname: str, billing_type: str,
                        custom_cost: float = None, notes: str = None) -> Dict:
        """Add a manual asset for a company."""
        data = {
            'hostname': hostname,
            'billing_type': billing_type
        }
        if custom_cost is not None:
            data['custom_cost'] = custom_cost
        if notes:
            data['notes'] = notes
        return self._call_ledger(f'/api/overrides/manual-assets/{account_number}', method='POST', data=data)

    def delete_manual_asset(self, account_number: str, asset_id: int) -> Dict:
        """Delete a manual asset."""
        return self._call_ledger(f'/api/overrides/manual-assets/{account_number}/{asset_id}', method='DELETE')

    # ===== MANUAL USERS =====

    def get_manual_users(self, account_number: str) -> List[Dict]:
        """Get all manual users for a company."""
        result = self._call_ledger(f'/api/overrides/manual-users/{account_number}')
        return result.get('manual_users', []) if isinstance(result, dict) else []

    def add_manual_user(self, account_number: str, full_name: str, billing_type: str,
                       custom_cost: float = None, notes: str = None) -> Dict:
        """Add a manual user for a company."""
        data = {
            'full_name': full_name,
            'billing_type': billing_type
        }
        if custom_cost is not None:
            data['custom_cost'] = custom_cost
        if notes:
            data['notes'] = notes
        return self._call_ledger(f'/api/overrides/manual-users/{account_number}', method='POST', data=data)

    def delete_manual_user(self, account_number: str, user_id: int) -> Dict:
        """Delete a manual user."""
        return self._call_ledger(f'/api/overrides/manual-users/{account_number}/{user_id}', method='DELETE')

    # ===== CUSTOM LINE ITEMS =====

    def get_custom_line_items(self, account_number: str) -> List[Dict]:
        """Get all custom line items for a company."""
        result = self._call_ledger(f'/api/overrides/line-items/{account_number}')
        return result.get('line_items', []) if isinstance(result, dict) else []

    def add_custom_line_item(self, account_number: str, name: str, **kwargs) -> Dict:
        """
        Add a custom line item for a company.

        Args:
            account_number: Company account number
            name: Line item name
            **kwargs: Optional fields (description, monthly_fee, one_off_fee, yearly_fee, etc.)
        """
        data = {'name': name}
        data.update(kwargs)
        return self._call_ledger(f'/api/overrides/line-items/{account_number}', method='POST', data=data)

    def update_custom_line_item(self, account_number: str, item_id: int, **kwargs) -> Dict:
        """Update a custom line item."""
        return self._call_ledger(f'/api/overrides/line-items/{account_number}/{item_id}',
                                method='PUT', data=kwargs)

    def delete_custom_line_item(self, account_number: str, item_id: int) -> Dict:
        """Delete a custom line item."""
        return self._call_ledger(f'/api/overrides/line-items/{account_number}/{item_id}', method='DELETE')

    # ===== INVOICE MANAGEMENT =====

    def get_invoice_summary(self, account_number: str, year: int, month: int) -> Dict:
        """Get invoice summary for a specific period."""
        return self._call_ledger(f'/api/invoice/{account_number}/summary?year={year}&month={month}')

    def check_bill_archived(self, account_number: str, year: int, month: int) -> Dict:
        """Check if a bill has been archived."""
        return self._call_ledger(f'/api/bill/check-archived/{account_number}?year={year}&month={month}')

    def accept_bill(self, account_number: str, year: int, month: int, notes: str = None) -> Dict:
        """Accept and archive a bill."""
        data = {
            'account_number': account_number,
            'year': year,
            'month': month
        }
        if notes:
            data['notes'] = notes
        return self._call_ledger('/api/bill/accept', method='POST', data=data)


# Global instance
_ledger_client = None

def get_ledger_client() -> LedgerClient:
    """Get the global LedgerClient instance."""
    global _ledger_client
    if _ledger_client is None:
        _ledger_client = LedgerClient()
    return _ledger_client
