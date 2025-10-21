#!/bin/bash
cd /home/david/Work/hivematrix/hivematrix-helm
source pyenv/bin/activate
TOKEN=$(python create_test_token.py 2>/dev/null | tail -1)

cd /home/david/Work/hivematrix/hivematrix-brainhair/ai_tools
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
