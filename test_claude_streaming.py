#!/usr/bin/env python3
"""
Test script to debug Claude Code streaming output.
This mimics what claude_session_manager.py does but with real-time debugging.
"""

import subprocess
import json
import select
import sys

def test_claude_streaming():
    """Test Claude Code streaming and show all events."""

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

    print(f"Running command: {' '.join(cmd[:4])}...\n")
    print("=" * 80)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )

    response_text = ""
    event_count = 0

    print("\n[STARTING STREAM]\n")

    # Stream both stdout and stderr
    while True:
        reads = [process.stdout, process.stderr]
        readable, _, _ = select.select(reads, [], [], 0.1)

        if not readable:
            if process.poll() is not None:
                print("\n[PROCESS FINISHED]")
                break
            continue

        for stream in readable:
            line = stream.readline()
            if not line:
                continue

            line = line.strip()
            if not line:
                continue

            # Check if stderr
            if stream == process.stderr:
                print(f"[STDERR] {line}")
                continue

            # Handle stdout JSON
            event_count += 1
            print(f"\n[EVENT #{event_count}]")

            try:
                event = json.loads(line)
                event_type = event.get('type')

                print(f"  Type: {event_type}")

                # Unwrap stream_event
                if event_type == 'stream_event':
                    inner_event = event.get('event', {})
                    inner_type = inner_event.get('type')
                    print(f"  → Unwrapped to: {inner_type}")
                    event = inner_event
                    event_type = inner_type

                # Handle different event types
                if event_type == 'content_block_delta':
                    delta = event.get('delta', {})
                    if delta.get('type') == 'text_delta':
                        text = delta.get('text', '')
                        response_text += text
                        print(f"  TEXT CHUNK: '{text}'")

                elif event_type == 'content_block_start':
                    content_block = event.get('content_block', {})
                    block_type = content_block.get('type')
                    print(f"  Content block: {block_type}")
                    if block_type == 'tool_use':
                        tool_name = content_block.get('name', '')
                        print(f"  → Tool: {tool_name}")

                elif event_type == 'assistant':
                    message = event.get('message', {})
                    content_blocks = message.get('content', [])
                    print(f"  Assistant message with {len(content_blocks)} blocks")
                    for block in content_blocks:
                        if block.get('type') == 'text':
                            text = block.get('text', '')
                            response_text += text
                            print(f"  TEXT: '{text}'")

                elif event_type == 'message_stop':
                    print("  → Message complete")
                    break

                elif event_type == 'result':
                    result_text = event.get('result', '')
                    print(f"  → Result: {result_text[:100]}")
                    break

                elif event_type == 'system':
                    subtype = event.get('subtype', '')
                    print(f"  Subtype: {subtype}")

                else:
                    print(f"  Other event: {json.dumps(event, indent=2)[:200]}")

            except json.JSONDecodeError as e:
                print(f"[JSON ERROR] {e}")
                print(f"  Line: {line[:200]}")

    process.wait(timeout=10)

    print("\n" + "=" * 80)
    print(f"\n[SUMMARY]")
    print(f"Total events: {event_count}")
    print(f"Exit code: {process.returncode}")
    print(f"Response text collected: '{response_text}'")
    print(f"Response length: {len(response_text)} chars")

    if not response_text:
        print("\n⚠️  WARNING: No response text was collected!")
        print("This means the text extraction logic is not working correctly.")
    else:
        print("\n✅ Response text successfully collected!")

    return response_text


if __name__ == '__main__':
    test_claude_streaming()
