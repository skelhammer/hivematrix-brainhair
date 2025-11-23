"""
Device/Asset Management Tools

Vendor-agnostic tools for interacting with device and asset information.
All data is retrieved from Codex service, which aggregates data from RMM providers.
"""

import os
import sys
import json

# Add parent directory to path to import service_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.service_client import call_service


def get_devices(company_account_number: str = None, status: str = None) -> dict:
    """
    Get list of managed devices from Codex.

    Codex aggregates device data from RMM providers (Datto, etc.) and provides
    a unified interface regardless of the underlying RMM system.

    Args:
        company_account_number: Filter by company account number (optional)
        status: Filter by status (optional): 'online', 'offline'

    Returns:
        {
            "devices": [
                {
                    "id": "device-123",
                    "name": "WORKSTATION-001",
                    "company_id": "965",
                    "company_name": "Acme Corporation",
                    "status": "online",
                    "os": "Windows 11 Pro",
                    "ip_address": "192.168.1.100",
                    "last_seen": "2025-11-23T12:00:00"
                },
                ...
            ],
            "count": 42
        }

    Example:
        >>> devices = get_devices(company_account_number='965', status='online')
        >>> for device in devices['devices']:
        ...     print(f"{device['name']} - {device['status']}")
    """
    try:
        params = {}
        if company_account_number:
            params['company_id'] = company_account_number
        if status:
            params['status'] = status

        query_string = '&'.join(f'{k}={v}' for k, v in params.items()) if params else ''
        url = f'/api/datto/devices?{query_string}' if query_string else '/api/datto/devices'

        response = call_service('codex', url)
        return response.json()
    except Exception as e:
        return {
            'error': f'Failed to retrieve devices: {str(e)}',
            'devices': [],
            'count': 0
        }


def get_device(device_id: str) -> dict:
    """
    Get detailed information about a specific device.

    Args:
        device_id: Device identifier (format: "device-123")

    Returns:
        {
            "id": "device-123",
            "name": "WORKSTATION-001",
            "company_id": "965",
            "company_name": "Acme Corporation",
            "status": "online",
            "os": "Windows 11 Pro",
            "os_version": "10.0.22631",
            "ip_address": "192.168.1.100",
            "mac_address": "XX:XX:XX:XX:XX:XX",
            "last_seen": "2025-11-23T12:00:00",
            "last_logged_in_user": "jsmith",
            "domain": "ACMECORP",
            "antivirus": "Windows Defender",
            "installed_software": [
                {"name": "Microsoft Office", "version": "16.0"},
                ...
            ],
            "hardware": {
                "cpu": "Intel Core i7",
                "ram_gb": 16,
                "disk_gb": 512
            },
            "health": {
                "cpu_usage": 15,
                "ram_usage": 45,
                "disk_usage": 60
            }
        }

    Example:
        >>> device = get_device("device-123")
        >>> print(f"Device: {device['name']}")
        >>> print(f"CPU Usage: {device['health']['cpu_usage']}%")
    """
    try:
        response = call_service('codex', f'/api/datto/device/{device_id}')
        return response.json()
    except Exception as e:
        return {
            'error': f'Failed to retrieve device details: {str(e)}',
            'id': device_id
        }


def get_company_assets(company_account_number: str) -> dict:
    """
    Get all assets (devices, computers) for a specific company.

    This provides more detailed asset information than the general device list.

    Args:
        company_account_number: Company account number (e.g., "965")

    Returns:
        [
            {
                "id": 123,
                "hostname": "WORKSTATION-001",
                "hardware_type": "Desktop",
                "operating_system": "Windows 11 Pro",
                "device_type": "Workstation",
                "last_logged_in_user": "jsmith",
                "antivirus_product": "Windows Defender",
                "ext_ip_address": "203.0.113.45",
                "int_ip_address": "192.168.1.100",
                "domain": "ACMECORP",
                "online": true,
                "last_seen": "2025-11-23T12:00:00",
                "backup_usage_tb": 0.5,
                "backup_data_bytes": 549755813888
            },
            ...
        ]

    Example:
        >>> assets = get_company_assets("965")
        >>> online_count = sum(1 for a in assets if a['online'])
        >>> print(f"Online devices: {online_count}/{len(assets)}")
    """
    try:
        response = call_service('codex', f'/api/companies/{company_account_number}/assets')
        return response.json()
    except Exception as e:
        return {
            'error': f'Failed to retrieve company assets: {str(e)}',
            'assets': []
        }


def execute_command(device_id: str, command: str, reason: str) -> dict:
    """
    Execute a PowerShell command on a remote device.

    ⚠️ IMPORTANT: This function REQUIRES HUMAN APPROVAL before execution.
    The command will be queued and displayed to the user for approval.

    Args:
        device_id: Device identifier
        command: PowerShell command to execute
        reason: Clear explanation of why this command is needed

    Returns:
        {
            "approval_required": true,
            "device_id": "device-123",
            "command": "Get-ComputerInfo",
            "reason": "Check system information for troubleshooting",
            "status": "pending_approval"
        }

    Example:
        >>> result = execute_command(
        ...     "device-123",
        ...     "Get-PSDrive C | Select-Object Used,Free",
        ...     "Check disk space for ticket #12345"
        ... )
        >>> if result['approval_required']:
        ...     print(f"Waiting for approval...")

    Safety Notes:
        - All commands are logged for audit purposes
        - Only approved technicians can approve commands
        - Dangerous commands should be explained clearly in the reason
        - Read-only commands (Get-*, Test-*, Show-*) are preferred
    """
    # This needs to go through Brainhair's approval system
    # We'll signal to the session manager that approval is needed

    # Output special marker for session manager to intercept
    approval_data = {
        'tool': 'execute_command',
        'device_id': device_id,
        'command': command,
        'reason': reason
    }

    # Print marker that session manager will intercept
    print(f'__TOOL_CALL__{json.dumps(approval_data)}')

    # Return pending status (actual execution happens after approval)
    return {
        'approval_required': True,
        'device_id': device_id,
        'command': command,
        'reason': reason,
        'status': 'pending_approval',
        'message': 'Command submitted for approval. Please wait for technician approval.'
    }
