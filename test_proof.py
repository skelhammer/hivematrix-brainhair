#!/usr/bin/env python3
"""
Proof test - mimics exactly what claude_session_manager.py does.
Shows timestamped output to prove streaming works.
"""

import subprocess
import json
import sys
from datetime import datetime

def timestamp():
    """Get current timestamp."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def test_session_manager_logic():
    """Test the exact logic from claude_session_manager.py"""

    claude_bin = '/home/david/.npm/_npx/becf7b9e49303068/node_modules/.bin/claude'

    # Build a realistic prompt like the session manager does
    system_prompt = """You are Brain Hair, an AI assistant for technical support.

## Current Context

- **Technician**: test_user
- **Ticket**: Not set
- **Client**: Not set"""

    message = "What is 2+2? Also tell me what 5+5 is. Be brief."

    cmd = [
        claude_bin,
        '--model', 'claude-sonnet-4-5',
        '--dangerously-skip-permissions',
        '--verbose',
        '--print',
        '--output-format', 'stream-json',
        '--include-partial-messages',
        '--append-system-prompt', system_prompt,
        message
    ]

    print(f"[{timestamp()}] Starting Claude Code process...")
    print(f"[{timestamp()}] Command: {' '.join(cmd[:4])}...")
    print("=" * 80)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr - exactly like session manager
        text=True,
        bufsize=1,  # Line buffered - exactly like session manager
    )

    response_text = ""
    chunk_count = 0

    print(f"[{timestamp()}] ⏳ Waiting for response...\n")

    # Stream output line by line - EXACT LOGIC from session manager
    for line in iter(process.stdout.readline, ''):
        if not line or not line.strip():
            continue

        line = line.strip()

        try:
            # Parse the JSON event
            event = json.loads(line)
            event_type = event.get('type')

            # Unwrap stream_event wrapper
            if event_type == 'stream_event':
                inner_event = event.get('event', {})
                event_type = inner_event.get('type')
                event = inner_event

            # Handle content_block_delta for streaming text chunks
            if event_type == 'content_block_delta':
                delta = event.get('delta', {})
                delta_type = delta.get('type')

                if delta_type == 'text_delta':
                    # Streaming text chunk - THIS IS WHAT USER SEES
                    text = delta.get('text', '')
                    response_text += text
                    chunk_count += 1
                    print(f"[{timestamp()}] 📝 CHUNK #{chunk_count}: '{text}'")

            # Handle content_block_start for tool calls
            elif event_type == 'content_block_start':
                content_block = event.get('content_block', {})
                block_type = content_block.get('type')

                if block_type == 'tool_use':
                    tool_name = content_block.get('name', 'unknown')
                    print(f"[{timestamp()}] 🔧 Using tool: {tool_name}")

            # Skip assistant message - we already got the text from deltas
            elif event_type == 'assistant':
                print(f"[{timestamp()}] ℹ️  Assistant message (already streamed)")
                pass

            elif event_type == 'message_stop':
                print(f"[{timestamp()}] ✅ Message complete")
                break

            elif event_type == 'result':
                print(f"[{timestamp()}] ✅ Result received")
                break

            elif event_type == 'system':
                print(f"[{timestamp()}] 💬 Live: Initializing Claude Code...")

            elif event_type == 'message_start':
                print(f"[{timestamp()}] 💬 Live: Claude is responding...")

            elif event_type == 'user':
                pass

            elif event_type == 'content_block_stop':
                print(f"[{timestamp()}] ℹ️  Content block finished")

            elif event_type == 'message_delta':
                pass

            else:
                print(f"[{timestamp()}] ❓ Unknown event: {event_type}")

        except json.JSONDecodeError:
            # Not JSON - treat as live message
            print(f"[{timestamp()}] 💬 Live: {line[:80]}")

    process.wait(timeout=30)

    print("\n" + "=" * 80)
    print(f"[{timestamp()}] TEST COMPLETE")
    print(f"Total text chunks: {chunk_count}")
    print(f"Exit code: {process.returncode}")
    print(f"Full response text: '{response_text}'")
    print(f"Response length: {len(response_text)} chars")

    if chunk_count > 0 and response_text:
        print(f"\n[{timestamp()}] ✅ SUCCESS - Streaming works!")
        print(f"[{timestamp()}] ✅ Got {chunk_count} chunks in real-time")
        print(f"[{timestamp()}] ✅ Total response: {len(response_text)} characters")
        return True
    else:
        print(f"\n[{timestamp()}] ❌ FAILED - No streaming detected")
        return False


if __name__ == '__main__':
    success = test_session_manager_logic()
    sys.exit(0 if success else 1)
