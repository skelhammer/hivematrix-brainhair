"""
Session Management Tools

Tools for managing the current chat session (setting title, etc).
"""

import os
import json
import requests
from typing import Optional


def set_chat_title(title: str) -> dict:
    """
    Set the title for the current chat session.

    This should be called early in the conversation (ideally after the first user message)
    to give the chat a descriptive title for the history list.

    Args:
        title: A short, descriptive title (3-6 words) summarizing the chat topic
               Examples: "Example Company Billing Setup", "Password Reset Issue",
                        "Server Performance Investigation"

    Returns:
        dict with 'success' and 'title' keys

    Example:
        >>> set_chat_title("Example Company Contract Alignment")
        {'success': True, 'title': 'Example Company Contract Alignment'}
    """
    try:
        # Get session ID from environment (set by ClaudeSession)
        context = os.environ.get('HIVEMATRIX_CONTEXT', '{}')
        context_data = json.loads(context)

        # Session ID is stored when the session starts
        session_id = os.environ.get('BRAINHAIR_SESSION_ID')

        if not session_id:
            return {
                'success': False,
                'error': 'No active session ID found'
            }

        # Call Brainhair API to update title
        brainhair_url = os.environ.get('BRAINHAIR_URL', 'http://localhost:5050')
        core_url = os.environ.get('CORE_SERVICE_URL', 'http://localhost:5000')

        # Get service token
        token_response = requests.post(
            f"{core_url}/service-token",
            json={
                "calling_service": "brainhair-tools",
                "target_service": "brainhair"
            },
            timeout=5
        )

        if token_response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to get service token: {token_response.status_code}'
            }

        token = token_response.json()['token']

        # Update session title
        response = requests.put(
            f"{brainhair_url}/api/chat/session/{session_id}/title",
            json={'title': title},
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )

        if response.status_code == 200:
            return {
                'success': True,
                'title': title
            }
        else:
            return {
                'success': False,
                'error': f'Failed to update title: {response.status_code} {response.text}'
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_current_session_info() -> dict:
    """
    Get information about the current chat session.

    Returns:
        dict with session information including ID, title, context
    """
    try:
        context = os.environ.get('HIVEMATRIX_CONTEXT', '{}')
        context_data = json.loads(context)
        session_id = os.environ.get('BRAINHAIR_SESSION_ID')

        return {
            'session_id': session_id,
            'context': context_data,
            'user': os.environ.get('HIVEMATRIX_USER')
        }
    except Exception as e:
        return {
            'error': str(e)
        }
