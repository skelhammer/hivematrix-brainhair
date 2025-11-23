#!/usr/bin/env python3
"""
Approval Helper

Helper functions for tools that need user approval before making changes.
"""

import os
import sys
import time
import json


def request_approval(action: str, details: dict, timeout: int = 120) -> bool:
    """
    Request approval from the user for a write operation.

    This sends an approval request as a JSON chunk to stdout, which gets
    streamed to the browser. The browser shows a modal and responds by
    writing to a file that we poll.

    Args:
        action: Description of the action (e.g., "Update per-user cost to $100")
        details: Dict with details to show user (e.g., {'company': 'Company Name', 'old_value': '$125', 'new_value': '$100'})
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
        print("ERROR: No active session ID found", file=sys.stderr)
        return False

    # Validate session ID format to prevent path traversal
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        print(f"ERROR: Invalid session ID format", file=sys.stderr)
        return False

    # Generate unique approval ID
    approval_id = f"{session_id}_{int(time.time() * 1000)}"  # Session ID + timestamp

    # Create request and response file paths
    request_file = f"/tmp/brainhair_approval_request_{approval_id}.json"
    response_file = f"/tmp/brainhair_approval_response_{approval_id}.json"

    # Write approval request to file (chat polling will pick it up)
    approval_request = {
        'type': 'approval_request',
        'approval_id': approval_id,
        'session_id': session_id,
        'action': action,
        'details': details
    }

    with open(request_file, 'w') as f:
        json.dump(approval_request, f)

    # Show waiting message to Claude (stderr goes to logs)
    print(f"\n⏳ Waiting for user approval...", file=sys.stderr)
    print(f"   Action: {action}", file=sys.stderr)
    for key, value in details.items():
        print(f"   {key}: {value}", file=sys.stderr)

    # Poll for response file
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(response_file):
            try:
                with open(response_file, 'r') as f:
                    response = json.load(f)

                # Clean up files
                os.remove(response_file)
                if os.path.exists(request_file):
                    os.remove(request_file)

                if response.get('approved'):
                    print("✓ User approved the change", file=sys.stderr)
                    return True
                else:
                    print("✗ User denied the change", file=sys.stderr)
                    return False

            except Exception as e:
                print(f"ERROR: Failed to read response: {e}", file=sys.stderr)
                # Clean up request file on error
                if os.path.exists(request_file):
                    os.remove(request_file)
                return False

        # Wait a bit before checking again
        time.sleep(0.5)

    # Timeout - clean up request file
    if os.path.exists(request_file):
        os.remove(request_file)
    print(f"ERROR: Approval timeout after {timeout} seconds", file=sys.stderr)
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
