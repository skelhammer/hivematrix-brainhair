#!/usr/bin/env python3
"""
Brain Hair Authentication Helper

Handles login and token management for Brain Hair API access.
"""

import requests
import json
import os
from typing import Optional, Dict


class BrainHairAuth:
    """Handle authentication for Brain Hair API."""

    def __init__(self, base_url: str = "https://localhost:443"):
        """
        Initialize authentication helper.

        Args:
            base_url: Base URL for Nexus gateway (default: https://localhost:443)
        """
        self.base_url = base_url.rstrip('/')
        self.brainhair_url = f"{base_url}/brainhair"
        self.token = None
        self.session = requests.Session()
        # Disable SSL verification for localhost (self-signed certs)
        self.session.verify = False
        # Suppress InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def login(self, username: str, password: str) -> bool:
        """
        Login to HiveMatrix and get a session token.

        Args:
            username: Username
            password: Password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Login through Nexus
            login_url = f"{self.base_url}/login"
            response = self.session.post(
                login_url,
                data={'username': username, 'password': password},
                allow_redirects=True
            )

            if response.status_code == 200:
                # Session cookie should be set
                return True
            else:
                print(f"Login failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"Login error: {e}")
            return False

    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """
        Make authenticated GET request to Brain Hair API.

        Args:
            endpoint: API endpoint (e.g., '/api/health')
            params: Query parameters

        Returns:
            Response object
        """
        url = f"{self.brainhair_url}{endpoint}"
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return self.session.get(url, params=params, headers=headers)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """
        Make authenticated POST request to Brain Hair API.

        Args:
            endpoint: API endpoint
            data: POST data

        Returns:
            Response object
        """
        url = f"{self.brainhair_url}{endpoint}"
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return self.session.post(url, json=data, headers=headers)


# Global instance for easy import
_auth = None


def get_auth(username: str = "claude", password: str = "claude123",
             base_url: str = None) -> BrainHairAuth:
    """
    Get or create authenticated Brain Hair client using service tokens.

    Args:
        username: Username (default: claude) - not used with service tokens
        password: Password (default: claude123) - not used with service tokens
        base_url: Base URL (default: auto-detect based on environment)

    Returns:
        Authenticated BrainHairAuth instance with service token
    """
    global _auth

    if _auth is None:
        # Always use service token authentication from Core
        # This works both from Claude Code and external tools
        base_url = "http://localhost:5050"
        _auth = BrainHairAuth(base_url)
        _auth.brainhair_url = base_url

        # Get service token from Core
        core_url = os.environ.get('CORE_SERVICE_URL', 'http://localhost:5000')
        try:
            response = requests.post(
                f"{core_url}/service-token",
                json={
                    "calling_service": "brainhair-tools",
                    "target_service": "brainhair"
                },
                timeout=5
            )
            if response.status_code == 200:
                _auth.token = response.json()['token']
            else:
                raise Exception(f"Failed to get service token: {response.status_code} {response.text}")
        except Exception as e:
            raise Exception(f"Failed to get service token from Core: {e}")

    return _auth


if __name__ == "__main__":
    # Test authentication
    auth = get_auth()
    response = auth.get("/api/health")
    print(f"Health check: {response.status_code}")
    if response.status_code == 200:
        try:
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print(f"Response: {response.text[:200]}")
