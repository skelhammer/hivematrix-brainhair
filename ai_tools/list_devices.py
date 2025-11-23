#!/usr/bin/env python3
"""
List Devices from RMM

Retrieves and displays all devices/computers from the RMM system (vendor-agnostic).
"""

import json
import sys
from brainhair_auth import get_auth


def list_devices(company_id=None):
    """
    List all devices with automatic compliance-based filtering.

    Filtering is applied automatically based on each company's compliance_level
    (Standard, CJIS, or HIPAA) as configured in Codex.

    Args:
        company_id: Optional company ID to filter by

    Returns:
        List of devices with appropriate compliance filtering applied
    """
    auth = get_auth()

    params = {}
    if company_id:
        params["company_id"] = company_id

    response = auth.get("/api/rmm/devices", params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('data', [])
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return []


def main():
    """Main entry point."""
    company_id = None

    if len(sys.argv) > 1:
        company_id = sys.argv[1]

    devices = list_devices(company_id)

    print(f"\n=== Devices ===\n")
    print("(Compliance filtering applied automatically per company)\n")

    if isinstance(devices, list):
        for device in devices:
            if isinstance(device, dict):
                print(f"ID: {device.get('id')}")
                print(f"Hostname: {device.get('hostname', 'N/A')}")
                print(f"Type: {device.get('type', 'N/A')}")
                print(f"Status: {device.get('status', 'N/A')}")
                print(f"Company: {device.get('company', 'N/A')}")
                print("-" * 40)
    else:
        print(json.dumps(devices, indent=2))

    print(f"\nTotal: {len(devices) if isinstance(devices, list) else 'N/A'}")


if __name__ == "__main__":
    main()
