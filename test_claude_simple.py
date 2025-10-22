#!/usr/bin/env python3
"""
Simpler test - just read stdout line by line.
"""

import subprocess
import json
import sys

claude_bin = '/home/david/.npm/_npx/becf7b9e49303068/node_modules/.bin/claude'
cmd = [
    claude_bin,
    '--model', 'claude-sonnet-4-5',
    '--dangerously-skip-permissions',
    '--verbose',
    '--print',
    '--output-format', 'stream-json',
    '--include-partial-messages',
    'What is 2+2? Reply with just the number.'
]

print(f"Running: {' '.join(cmd[:4])}...")
print("=" * 80)

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # Merge stderr into stdout
    text=True,
    bufsize=1,  # Line buffered
)

response_text = ""
event_count = 0

for line in iter(process.stdout.readline, ''):
    if not line.strip():
        continue

    event_count += 1
    line = line.strip()

    print(f"\n[EVENT #{event_count}]")
    print(f"Raw: {line[:150]}")

    try:
        event = json.loads(line)
        event_type = event.get('type')
        print(f"Type: {event_type}")

        # Unwrap stream_event
        if event_type == 'stream_event':
            inner = event.get('event', {})
            event_type = inner.get('type')
            event = inner
            print(f"  → Unwrapped: {event_type}")

        # Extract text
        if event_type == 'content_block_delta':
            delta = event.get('delta', {})
            if delta.get('type') == 'text_delta':
                text = delta.get('text', '')
                response_text += text
                print(f"  ✓ TEXT: '{text}'")

        elif event_type == 'assistant':
            for block in event.get('message', {}).get('content', []):
                if block.get('type') == 'text':
                    text = block.get('text', '')
                    response_text += text
                    print(f"  ✓ TEXT: '{text}'")

        elif event_type in ['message_stop', 'result']:
            print("  → DONE")
            break

    except json.JSONDecodeError:
        print("  (not JSON)")

process.wait()

print("\n" + "=" * 80)
print(f"Events: {event_count}")
print(f"Exit code: {process.returncode}")
print(f"Response: '{response_text}'")

if response_text:
    print("\n✅ SUCCESS - Got response text!")
else:
    print("\n❌ FAILED - No response text!")
