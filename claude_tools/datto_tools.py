"""
Datto RMM Service Tools

Tools for interacting with devices and executing remote commands.
Commands that modify systems require human approval.
"""

import os
import sys
import json

# Add parent directory to path to import service_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.service_client import call_service


def get_devices(company_id: int = None, status: str = None) -> dict:
    """
    Get list of devices from Datto RMM.

    Args:
        company_id: Filter by company ID (optional)
        status: Filter by status (optional): 'online', 'offline', 'warning'

    Returns:
        {
            "devices": [
                {
                    "id": "device-123",
                    "name": "WORKSTATION-001",
                    "company_id": 1,
                    "company_name": "Company Name",
                    "status": "online",
                    "os": "Windows 11 Pro",
                    "ip_address": "XXX.XXX.XXX.XXX",  # Filtered
                    "last_seen": "2025-10-21T12:00:00"
                },
                ...
            ],
            "count": 42
        }

    Example:
        >>> devices = get_devices(company_id=1, status='online')
        >>> for device in devices['devices']:
        ...     print(f"{device['name']} - {device['status']}")
    """
    try:
        params = {}
        if company_id:
            params['company_id'] = company_id
        if status:
            params['status'] = status

        query_string = '&'.join(f'{k}={v}' for k, v in params.items()) if params else ''
        url = f'/api/datto/devices?{query_string}' if query_string else '/api/datto/devices'

        response = call_service('codex', url)
        return response.json()
    except Exception as e:
        return {
            'error': 'Failed to retrieve devices',
            'devices': [],
            'count': 0
        }


def get_device(device_id: str) -> dict:
    """
    Get detailed information about a specific device.

    Args:
        device_id: Device identifier

    Returns:
        {
            "id": "device-123",
            "name": "WORKSTATION-001",
            "company_id": 1,
            "company_name": "Company Name",
            "status": "online",
            "os": "Windows 11 Pro",
            "os_version": "10.0.22631",
            "ip_address": "XXX.XXX.XXX.XXX",  # Filtered
            "mac_address": "XX:XX:XX:XX:XX:XX",  # Filtered
            "last_seen": "2025-10-21T12:00:00",
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
            'error': 'Failed to retrieve device details',
            'id': device_id
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
            "command_id": "cmd-uuid",
            "device_id": "device-123",
            "device_name": "WORKSTATION-001",
            "command": "Get-ComputerInfo",
            "reason": "Check system information for troubleshooting",
            "status": "pending_approval"
        }

        After approval, the result will be:
        {
            "success": true,
            "command_id": "cmd-uuid",
            "output": "Command output here...",
            "executed_at": "2025-10-21T12:05:00"
        }

    Example:
        >>> # Request to check disk space
        >>> result = execute_command(
        ...     "device-123",
        ...     "Get-PSDrive C | Select-Object Used,Free",
        ...     "Check disk space for ticket #12345"
        ... )
        >>> if result['approval_required']:
        ...     print(f"Waiting for approval: {result['command_id']}")

    Safety Notes:
        - All commands are logged for audit purposes
        - Only approved technicians can approve commands
        - Dangerous commands should be explained clearly in the reason
        - Read-only commands (Get-*, Test-*, Show-*) are preferred
    """
    # This needs to go through Brain Hair's approval system
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


def get_command_status(command_id: str) -> dict:
    """
    Check the status of a command execution.

    Args:
        command_id: Command identifier from execute_command

    Returns:
        {
            "command_id": "cmd-uuid",
            "status": "pending_approval" | "approved" | "denied" | "executed" | "failed",
            "output": "Command output (if executed)",
            "error": "Error message (if failed)",
            "executed_at": "2025-10-21T12:05:00",
            "executed_by": "Tech Name"
        }

    Example:
        >>> status = get_command_status("cmd-uuid")
        >>> print(f"Status: {status['status']}")
        >>> if status['status'] == 'executed':
        ...     print(f"Output: {status['output']}")
    """
    try:
        response = call_service('brainhair', f'/api/command/{command_id}/status')
        return response.json()
    except Exception as e:
        return {
            'error': 'Failed to retrieve command status',
            'command_id': command_id,
            'status': 'unknown'
        }
