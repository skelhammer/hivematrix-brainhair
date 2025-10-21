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
        return self.session.get(url, params=params)

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
        return self.session.post(url, json=data)


# Global instance for easy import
_auth = None


def get_auth(username: str = "claude", password: str = "claude123",
             base_url: str = None) -> BrainHairAuth:
    """
    Get or create authenticated Brain Hair client.

    Args:
        username: Username (default: claude)
        password: Password (default: claude123)
        base_url: Base URL (default: auto-detect based on environment)

    Returns:
        Authenticated BrainHairAuth instance
    """
    global _auth

    if _auth is None:
        # Check if we're running from Claude Code (internal) or external
        # If HIVEMATRIX_USER is set, we're running from Claude Code
        if os.environ.get('HIVEMATRIX_USER'):
            # Running from Claude Code - connect directly to local Brain Hair without auth
            # Brain Hair trusts local connections from Claude
            base_url = "http://localhost:5050"
            _auth = BrainHairAuth(base_url)
            _auth.brainhair_url = base_url  # Use Brain Hair directly, not through gateway
            # No login needed for local connections
        else:
            # Running externally - use Nexus gateway with auth
            if base_url is None:
                base_url = "https://localhost:443"
            _auth = BrainHairAuth(base_url)
            if not _auth.login(username, password):
                raise Exception("Authentication failed")

    return _auth


if __name__ == "__main__":
    # Test authentication
    auth = get_auth()
    response = auth.get("/api/health")
    print(f"Health check: {response.status_code}")
    if response.status_code == 200:
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(f"Response: {response.text[:200]}")
