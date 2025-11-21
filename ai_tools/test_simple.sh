#!/bin/bash
# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HIVEMATRIX_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$HIVEMATRIX_ROOT/hivematrix-helm"
source pyenv/bin/activate
TOKEN=$(python create_test_token.py 2>/dev/null | tail -1)

cd "$SCRIPT_DIR"
python3 << EOF
from brainhair_simple import SimpleBrainHairClient

token = """$TOKEN"""
client = SimpleBrainHairClient(token)
response = client.get('/api/health')
print(f'Health check: {response.status_code}')
if response.status_code == 200:
    import json
    print(json.dumps(response.json(), indent=2))
EOF
