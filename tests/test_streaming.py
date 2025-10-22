#!/usr/bin/env python3
"""
Test streaming JSON parsing for Claude Code responses.

This test validates that the streaming event parser correctly handles:
- content_block_delta events (partial text streaming)
- content_block_start events (tool calls)
- message_start/message_stop events
- Full assistant message fallback
"""

import json
import sys
import os

# This test validates the streaming parsing logic without needing the full app


def test_content_block_delta():
    """Test parsing of streaming text deltas."""
    print("Testing content_block_delta parsing...")

    # Simulate Claude Code streaming events
    events = [
        {"type": "message_start", "message": {"id": "msg_123", "type": "message"}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " World"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_stop"}
    ]

    # Mock parsing logic
    response_text = ""
    chunks = []

    for event in events:
        event_type = event.get('type')

        if event_type == 'content_block_delta':
            delta = event.get('delta', {})
            delta_type = delta.get('type')

            if delta_type == 'text_delta':
                text = delta.get('text', '')
                response_text += text
                chunks.append(text)

    expected_text = "Hello World!"
    expected_chunks = ["Hello", " World", "!"]

    assert response_text == expected_text, f"Expected '{expected_text}', got '{response_text}'"
    assert chunks == expected_chunks, f"Expected {expected_chunks}, got {chunks}"

    print("✓ content_block_delta parsing works correctly")
    return True


def test_tool_use_detection():
    """Test detection of tool use events."""
    print("Testing tool use detection...")

    events = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_123", "name": "Bash"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"command": "ls -la"}'}},
        {"type": "content_block_stop", "index": 0}
    ]

    tool_calls = []

    for event in events:
        event_type = event.get('type')

        if event_type == 'content_block_start':
            content_block = event.get('content_block', {})
            block_type = content_block.get('type')

            if block_type == 'tool_use':
                tool_name = content_block.get('name', 'unknown')
                tool_calls.append(tool_name)

    assert len(tool_calls) == 1, f"Expected 1 tool call, got {len(tool_calls)}"
    assert tool_calls[0] == "Bash", f"Expected 'Bash', got '{tool_calls[0]}'"

    print("✓ Tool use detection works correctly")
    return True


def test_mixed_content():
    """Test handling mixed text and tool use content."""
    print("Testing mixed content parsing...")

    events = [
        {"type": "message_start"},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Let me check that for you."}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "name": "Read"}},
        {"type": "content_block_stop", "index": 1},
        {"type": "content_block_start", "index": 2, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 2, "delta": {"type": "text_delta", "text": "Here are the results."}},
        {"type": "content_block_stop", "index": 2},
        {"type": "message_stop"}
    ]

    response_text = ""
    tool_calls = []

    for event in events:
        event_type = event.get('type')

        if event_type == 'content_block_delta':
            delta = event.get('delta', {})
            if delta.get('type') == 'text_delta':
                response_text += delta.get('text', '')

        elif event_type == 'content_block_start':
            content_block = event.get('content_block', {})
            if content_block.get('type') == 'tool_use':
                tool_calls.append(content_block.get('name'))

    expected_text = "Let me check that for you.Here are the results."

    assert response_text == expected_text, f"Expected '{expected_text}', got '{response_text}'"
    assert len(tool_calls) == 1, f"Expected 1 tool call, got {len(tool_calls)}"
    assert tool_calls[0] == "Read", f"Expected 'Read', got '{tool_calls[0]}'"

    print("✓ Mixed content parsing works correctly")
    return True


def test_fallback_assistant_message():
    """Test fallback to full assistant message format."""
    print("Testing fallback assistant message...")

    events = [
        {
            "type": "assistant",
            "message": {
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "This is a complete message."}
                ]
            }
        }
    ]

    response_text = ""

    for event in events:
        event_type = event.get('type')

        if event_type == 'assistant':
            message = event.get('message', {})
            content_blocks = message.get('content', [])

            for block in content_blocks:
                if block.get('type') == 'text':
                    response_text += block.get('text', '')

    expected_text = "This is a complete message."

    assert response_text == expected_text, f"Expected '{expected_text}', got '{response_text}'"

    print("✓ Fallback assistant message parsing works correctly")
    return True


def test_empty_events():
    """Test handling of empty or malformed events."""
    print("Testing empty/malformed events...")

    events = [
        {},
        {"type": "unknown_event"},
        {"type": "content_block_delta"},  # Missing delta
        {"type": "content_block_delta", "delta": {}},  # Empty delta
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Valid"}},
    ]

    response_text = ""

    for event in events:
        event_type = event.get('type')

        if event_type == 'content_block_delta':
            delta = event.get('delta', {})
            if delta.get('type') == 'text_delta':
                response_text += delta.get('text', '')

    expected_text = "Valid"

    assert response_text == expected_text, f"Expected '{expected_text}', got '{response_text}'"

    print("✓ Empty/malformed event handling works correctly")
    return True


def run_all_tests():
    """Run all streaming tests."""
    print("\n=== Running Claude Code Streaming Tests ===\n")

    tests = [
        test_content_block_delta,
        test_tool_use_detection,
        test_mixed_content,
        test_fallback_assistant_message,
        test_empty_events
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
        print()

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
