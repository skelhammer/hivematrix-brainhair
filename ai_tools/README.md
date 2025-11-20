# Brain Hair AI Tools

This directory contains Python scripts that Claude can use to interact with the HiveMatrix system through the Brain Hair API gateway. All data is automatically filtered for PHI/CJIS compliance using Presidio.

## Authentication

All tools use the `brainhair_auth.py` module for authentication. Default credentials:
- Username: `claude`
- Password: `claude123`

## Available Tools

### 1. brainhair_auth.py
Authentication helper and base client for all other tools.

**Test:**
```bash
python brainhair_auth.py
```

### 2. list_companies.py
List all companies from Codex.

**Usage:**
```bash
python list_companies.py [filter]
```

**Examples:**
```bash
python list_companies.py          # PHI filtering (default)
python list_companies.py cjis     # CJIS filtering
```

### 3. list_devices.py
List devices/computers from Datto.

**Usage:**
```bash
python list_devices.py [company_id] [filter]
```

**Examples:**
```bash
python list_devices.py                # All devices, PHI filtering
python list_devices.py 123           # Devices for company 123
python list_devices.py phi           # PHI filtering
python list_devices.py 123 cjis      # Company 123, CJIS filtering
```

### 4. search_knowledge.py
Search and browse the KnowledgeTree.

**Usage:**
```bash
python search_knowledge.py search <query> [filter]
python search_knowledge.py browse [path] [filter]
```

**Examples:**
```bash
python search_knowledge.py search "password reset"
python search_knowledge.py search "VPN" cjis
python search_knowledge.py browse
python search_knowledge.py browse "/network/vpn"
```

### 5. list_tickets.py
List and view tickets from PSA or Codex.

**Usage:**
```bash
python list_tickets.py list [source] [filter]
python list_tickets.py get <ticket_id> [source] [filter]
```

**Examples:**
```bash
python list_tickets.py list                        # PSA tickets
python list_tickets.py list codex                  # Codex tickets
python list_tickets.py list psa cjis               # PSA with CJIS filter
python list_tickets.py get 12345                   # Get specific ticket
python list_tickets.py get 12345 codex phi         # Get from Codex with PHI filter
```

## Data Filtering

All tools support two filter types:

- **PHI** (default): Filters Protected Health Information
  - Names: Converted to "FirstName L." format (e.g., "John Smith" → "John S.")
  - Email addresses: Replaced with `<EMAIL_ADDRESS>`
  - Phone numbers: Replaced with `<PHONE_NUMBER>`
  - SSN, addresses, dates, etc.: Replaced with type labels

- **CJIS**: Filters Criminal Justice Information Systems data
  - Stricter filtering for law enforcement use cases
  - Similar to PHI but with additional restrictions

## Python API Usage

You can also import these modules and use them programmatically:

```python
from brainhair_auth import get_auth

# Authenticate
auth = get_auth()

# Make API calls
response = auth.get("/api/health")
print(response.json())

# Search knowledge
response = auth.get("/api/knowledge/search", params={"q": "VPN", "filter": "phi"})
results = response.json()

# List companies
response = auth.get("/api/codex/companies", params={"filter": "phi"})
companies = response.json()
```

## Environment Variables

Optional environment variables:
- `BRAINHAIR_URL`: Base URL (default: https://localhost:443)
- `BRAINHAIR_USERNAME`: Username (default: claude)
- `BRAINHAIR_PASSWORD`: Password (default: claude123)

## API Endpoints Reference

All available Brain Hair endpoints:

### Knowledge
- `GET /api/knowledge/search?q=<query>&filter=<phi|cjis>`
- `GET /api/knowledge/browse?path=<path>&filter=<phi|cjis>`
- `GET /api/knowledge/node/<id>?filter=<phi|cjis>`

### Codex
- `GET /api/codex/companies?filter=<phi|cjis>`
- `GET /api/codex/company/<id>?filter=<phi|cjis>`
- `GET /api/codex/tickets?company_id=<id>&status=<status>&filter=<phi|cjis>`

### PSA
- `GET /api/psa/tickets?limit=<n>&filter=<phi|cjis>`
- `GET /api/psa/ticket/<id>?filter=<phi|cjis>`

### Datto
- `GET /api/datto/devices?company_id=<id>&filter=<phi|cjis>`
- `GET /api/datto/device/<id>?filter=<phi|cjis>`

### Utility
- `GET /api/health` - Health check
- `GET /api/endpoints` - List all available endpoints

## Notes

- All tools require Brain Hair service to be running on port 5050
- Access is proxied through Nexus on port 443 (HTTPS)
- Self-signed SSL certificates are accepted for localhost
- All data is automatically filtered before being returned
- Names are converted to "FirstName L." format instead of being completely redacted
