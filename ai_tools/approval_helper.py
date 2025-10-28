#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Approval Helper

Helper functions for tools that need user approval before making changes.
"""

import os
import requests
import time
import json


def request_approval(action: str, details: dict, timeout: int = 120) -> bool:
    """
    Request approval from the user for a write operation.

    Args:
        action: Description of the action (e.g., "Update per-user cost to $100")
        details: Dict with details to show user (e.g., {'company': 'Example Company', 'old_value': '$125', 'new_value': '$100'})
        timeout: Seconds to wait for approval (default 120)

    Returns:
        True if approved, False if denied or timeout

    Example:
        >>> if request_approval("Update per-user cost", {'company': 'Example Company', 'from': '$125', 'to': '$100'}):
        >>>     # Make the change
        >>>     pass
        >>> else:
        >>>     print("ERROR: User denied the change")
        >>>     exit(1)
    """
    # Get session ID from environment
    session_id = os.environ.get('BRAINHAIR_SESSION_ID')
    if not session_id:
        print("ERROR: No active session ID found")
        return False

    # Service URLs
    brainhair_url = os.getenv('BRAINHAIR_URL', 'http://localhost:5050')
    core_url = os.getenv('CORE_SERVICE_URL', 'http://localhost:5000')

    # Get service token
    try:
        token_response = requests.post(
            f"{core_url}/service-token",
            json={
                "calling_service": "brainhair-tools",
                "target_service": "brainhair"
            },
            timeout=5
        )
        if token_response.status_code != 200:
            print(f"ERROR: Failed to get service token: {token_response.status_code}")
            return False

        token = token_response.json()['token']
        headers = {"Authorization": f"Bearer {token}"}

    except Exception as e:
        print(f"ERROR: Failed to get service token: {e}")
        return False

    # Create approval request
    try:
        response = requests.post(
            f"{brainhair_url}/api/approval/request",
            json={
                'session_id': session_id,
                'action': action,
                'details': details
            },
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            print(f"ERROR: Failed to create approval request: {response.status_code}")
            return False

        approval_id = response.json()['approval_id']
        print(f"\n⏳ Waiting for user approval...")
        print(f"   Action: {action}")
        for key, value in details.items():
            print(f"   {key}: {value}")

    except Exception as e:
        print(f"ERROR: Failed to create approval request: {e}")
        return False

    # Poll for approval
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{brainhair_url}/api/approval/poll/{approval_id}",
                headers=headers,
                timeout=5
            )

            if response.status_code != 200:
                print(f"ERROR: Failed to poll approval: {response.status_code}")
                return False

            data = response.json()
            status = data.get('status')

            if status == 'approved':
                print("✓ User approved the change")
                return True
            elif status == 'denied':
                print("✗ User denied the change")
                return False

            # Still pending, wait a bit
            time.sleep(1)

        except Exception as e:
            print(f"ERROR: Failed to poll approval: {e}")
            return False

    # Timeout
    print(f"ERROR: Approval timeout after {timeout} seconds")
    return False


if __name__ == "__main__":
    # Test
    approved = request_approval(
        "Update per-user cost",
        {
            'company': 'Test Company',
            'from': '$125/user',
            'to': '$100/user'
        }
    )
    print(f"Result: {'Approved' if approved else 'Denied'}")
