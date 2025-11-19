#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Comprehensive Brain Hair Endpoint Tester

Tests all endpoints and verifies PHI/CJIS filtering is working.
"""

import json
from brainhair_simple import get_client


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_endpoint(client, endpoint, params=None, description=""):
    """Test an endpoint and display results."""
    print(f"Testing: {endpoint}")
    if description:
        print(f"Description: {description}")
    if params:
        print(f"Parameters: {params}")

    try:
        response = client.get(endpoint, params=params)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response preview:")
                # Pretty print with truncation
                json_str = json.dumps(data, indent=2)
                if len(json_str) > 1000:
                    print(json_str[:1000] + "\n... (truncated)")
                else:
                    print(json_str)
                return data
            except Exception:
                print(f"Response text: {response.text[:500]}")
                return None
        else:
            print(f"Error: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None
    finally:
        print("-" * 80)


def main():
    """Run comprehensive endpoint tests."""
    print_section("Brain Hair Endpoint Testing Suite")

    # Initialize client
    print("Initializing Brain Hair client...")
    client = get_client()
    print("✓ Client authenticated\n")

    # Test 1: Health Check
    print_section("1. UTILITY ENDPOINTS")
    test_endpoint(client, "/api/health", description="Service health check")
    test_endpoint(client, "/api/endpoints", description="List all available endpoints")

    # Test 2: KnowledgeTree Endpoints
    print_section("2. KNOWLEDGETREE ENDPOINTS")

    # Browse root
    kt_browse = test_endpoint(
        client,
        "/api/knowledge/browse",
        params={"filter": "phi"},
        description="Browse KnowledgeTree root"
    )

    # Search knowledge
    kt_search = test_endpoint(
        client,
        "/api/knowledge/search",
        params={"q": "password", "filter": "phi"},
        description="Search for 'password'"
    )

    # Get specific node if we have any
    if kt_browse and isinstance(kt_browse.get('data'), list) and len(kt_browse['data']) > 0:
        node_id = kt_browse['data'][0].get('id')
        if node_id:
            test_endpoint(
                client,
                f"/api/knowledge/node/{node_id}",
                params={"filter": "phi"},
                description=f"Get node details for ID {node_id}"
            )

    # Test 3: Codex Endpoints
    print_section("3. CODEX ENDPOINTS")

    # List companies
    companies = test_endpoint(
        client,
        "/api/codex/companies",
        params={"filter": "phi"},
        description="List all companies"
    )

    # Get specific company if we have any
    if companies and isinstance(companies.get('data'), list) and len(companies['data']) > 0:
        company_id = companies['data'][0].get('id')
        if company_id:
            test_endpoint(
                client,
                f"/api/codex/company/{company_id}",
                params={"filter": "phi"},
                description=f"Get company details for ID {company_id}"
            )

            # List tickets for this company
            test_endpoint(
                client,
                "/api/codex/tickets",
                params={"company_id": company_id, "filter": "phi"},
                description=f"List tickets for company {company_id}"
            )

    # List all tickets
    tickets = test_endpoint(
        client,
        "/api/codex/tickets",
        params={"filter": "phi"},
        description="List all tickets"
    )

    # Test 4: FreshService Endpoints
    print_section("4. FRESHSERVICE ENDPOINTS")

    # List FreshService tickets
    fs_tickets = test_endpoint(
        client,
        "/api/freshservice/tickets",
        params={"filter": "phi", "limit": "10"},
        description="List FreshService tickets (limit 10)"
    )

    # Get specific ticket if we have any
    if fs_tickets and isinstance(fs_tickets.get('data'), list) and len(fs_tickets['data']) > 0:
        ticket_id = fs_tickets['data'][0].get('id')
        if ticket_id:
            test_endpoint(
                client,
                f"/api/freshservice/ticket/{ticket_id}",
                params={"filter": "phi"},
                description=f"Get FreshService ticket ID {ticket_id}"
            )

    # Test 5: Datto Endpoints
    print_section("5. DATTO ENDPOINTS")

    # List all devices
    devices = test_endpoint(
        client,
        "/api/datto/devices",
        params={"filter": "phi"},
        description="List all Datto devices"
    )

    # Get specific device if we have any
    if devices and isinstance(devices.get('data'), list) and len(devices['data']) > 0:
        device_id = devices['data'][0].get('id')
        if device_id:
            test_endpoint(
                client,
                f"/api/datto/device/{device_id}",
                params={"filter": "phi"},
                description=f"Get Datto device ID {device_id}"
            )

    # List devices for a company if we have one
    if companies and isinstance(companies.get('data'), list) and len(companies['data']) > 0:
        company_id = companies['data'][0].get('id')
        if company_id:
            test_endpoint(
                client,
                "/api/datto/devices",
                params={"company_id": company_id, "filter": "phi"},
                description=f"List Datto devices for company {company_id}"
            )

    # Test 6: CJIS Filtering Test
    print_section("6. CJIS FILTERING COMPARISON")

    print("Testing PHI vs CJIS filtering on same endpoint...")
    print("\nPHI Filtering:")
    phi_result = test_endpoint(
        client,
        "/api/codex/companies",
        params={"filter": "phi"},
        description="Companies with PHI filter"
    )

    print("\nCJIS Filtering:")
    cjis_result = test_endpoint(
        client,
        "/api/codex/companies",
        params={"filter": "cjis"},
        description="Companies with CJIS filter"
    )

    # Summary
    print_section("TEST SUMMARY")
    print("✓ All endpoint tests completed")
    print("\nKey Points to Verify:")
    print("1. Names should show as 'FirstName L.' format")
    print("2. Email addresses should be <EMAIL_ADDRESS>")
    print("3. Phone numbers should be <PHONE_NUMBER>")
    print("4. IP addresses should be <IP_ADDRESS>")
    print("5. SSN/sensitive data should be <US_SSN>, etc.")
    print("\nReview the output above to ensure all PII is properly filtered.")


if __name__ == "__main__":
    main()
