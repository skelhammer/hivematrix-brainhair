#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Set Chat Title

Sets the title for the current chat session.

Usage:
    python set_chat_title.py "Example Company Billing Setup"
"""

import sys
import os
import json
import requests

# Service URLs
CORE_URL = os.getenv('CORE_SERVICE_URL', 'http://localhost:5000')
BRAINHAIR_URL = os.getenv('BRAINHAIR_URL', 'http://localhost:5050')


def get_service_token(target_service):
    """Get service token from Core."""
    try:
        response = requests.post(
            f"{CORE_URL}/service-token",
            json={
                "calling_service": "brainhair-tools",
                "target_service": target_service
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["token"]
        return None
    except Exception as e:
        print(f"ERROR: Could not get service token: {e}")
        return None


def set_title(title):
    """Set the chat session title."""
    # Get session ID from environment
    session_id = os.environ.get('BRAINHAIR_SESSION_ID')

    if not session_id:
        print("ERROR: No active session ID found")
        print("This tool can only be called from within a Brainhair chat session")
        return False

    # Get service token
    token = get_service_token("brainhair")
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.put(
            f"{BRAINHAIR_URL}/api/chat/session/{session_id}/title",
            json={'title': title},
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            print(f"✓ Chat title set to: {title}")
            return True
        else:
            print(f"ERROR: Failed to set title: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python set_chat_title.py <title>")
        print("Example: python set_chat_title.py 'Example Company Billing Setup'")
        sys.exit(1)

    title = sys.argv[1]

    if not title or len(title) < 3:
        print("ERROR: Title must be at least 3 characters")
        sys.exit(1)

    if len(title) > 100:
        print("WARNING: Title truncated to 100 characters")
        title = title[:100]

    success = set_title(title)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
