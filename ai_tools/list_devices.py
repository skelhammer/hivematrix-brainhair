#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
List Devices from Datto

Retrieves and displays all devices/computers from Datto.
"""

import json
import sys
from brainhair_auth import get_auth


def list_devices(company_id=None, filter_type="phi"):
    """
    List all devices with PHI/CJIS filtering.

    Args:
        company_id: Optional company ID to filter by
        filter_type: Type of filter to apply ("phi" or "cjis")

    Returns:
        List of devices
    """
    auth = get_auth()

    params = {"filter": filter_type}
    if company_id:
        params["company_id"] = company_id

    response = auth.get("/api/datto/devices", params=params)

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
    filter_type = "phi"

    if len(sys.argv) > 1:
        if sys.argv[1] in ["phi", "cjis"]:
            filter_type = sys.argv[1]
        else:
            company_id = sys.argv[1]

    if len(sys.argv) > 2:
        filter_type = sys.argv[2]

    devices = list_devices(company_id, filter_type)

    print(f"\n=== Devices (Filter: {filter_type}) ===\n")

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
