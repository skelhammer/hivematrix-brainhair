#!/usr/bin/env python3
"""
Simplified Brain Hair Client - Direct API Access

Bypasses Nexus and connects directly to Brain Hair with a Bearer token.
For use in automated/AI scenarios.
"""

import requests
import json
import os
from typing import Optional, Dict
import urllib3

# Disable SSL warnings for localhost
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SimpleBrainHairClient:
    """Direct Brain Hair API client using Bearer tokens."""

    def __init__(self, token: Optional[str] = None, base_url: str = "http://localhost:5050"):
        """
        Initialize direct API client.

        Args:
            token: Bearer token for authentication
            base_url: Direct Brain Hair URL (default: http://localhost:5050)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.session.verify = False

        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """
        Make GET request to Brain Hair API.

        Args:
            endpoint: API endpoint (e.g., '/api/health')
            params: Query parameters

        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """
        Make POST request to Brain Hair API.

        Args:
            endpoint: API endpoint
            data: POST data

        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url, json=data)


def get_token_from_helm():
    """
    Get a test token from hivematrix-helm.

    Returns:
        Token string or None
    """
    import subprocess
    import sys

    # Try to run create_test_token.py from helm
    helm_path = os.path.join(os.path.dirname(__file__), '../../hivematrix-helm')

    if os.path.exists(helm_path):
        try:
            result = subprocess.run(
                [f'{helm_path}/pyenv/bin/python', f'{helm_path}/create_test_token.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Ignore deprecation warnings
                text=True,
                timeout=5,
                cwd=helm_path  # Run from helm directory
            )
            if result.returncode == 0:
                # Get last line which should be the token
                lines = result.stdout.strip().split('\n')
                return lines[-1] if lines else None
        except Exception as e:
            print(f"Could not get token from helm: {e}", file=sys.stderr)

    return None


# Global instance
_client = None


def get_client(token: Optional[str] = None, base_url: str = "http://localhost:5050") -> SimpleBrainHairClient:
    """
    Get or create Brain Hair client.

    Args:
        token: Bearer token (will try to get from helm if not provided)
        base_url: Brain Hair URL

    Returns:
        SimpleBrainHairClient instance
    """
    global _client

    if _client is None:
        if token is None:
            token = get_token_from_helm()

        if token is None:
            raise Exception("No authentication token available. Please provide a token or ensure helm is set up.")

        _client = SimpleBrainHairClient(token, base_url)

    return _client


if __name__ == "__main__":
    # Test direct access
    client = get_client()
    response = client.get("/api/health")
    print(f"Health check: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
