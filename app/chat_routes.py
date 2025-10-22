"""
Chat routes for Brain Hair AI Assistant

Handles chat interface, Claude Code integration, and command approval workflow.
"""

from flask import render_template, request, jsonify, g, Response, stream_with_context
from app import app
from .auth import token_required
from .service_client import call_service
from .helm_logger import get_helm_logger
from .claude_session_manager import get_session_manager
import json
import uuid
from typing import Dict, List, Any, Optional
import os

# Store pending commands (in production, use Redis or database)
pending_commands = {}

# Get the global session manager
session_manager = get_session_manager()


@app.route('/chat')
@token_required
def chat_interface():
    """
    Render the chat interface.
    """
    logger = get_helm_logger()

    # Prevent service calls from accessing UI
    if g.is_service_call:
        return jsonify({'error': 'This endpoint is for users only'}), 403

    user = g.user
    logger.info(f"User {user.get('preferred_username')} accessed chat interface")

    return render_template('chat.html', user=user)


# Store for polling-based responses
response_buffers = {}

@app.route('/api/chat', methods=['POST'])
@token_required
def chat_message():
    """
    Handle chat messages using polling instead of SSE.

    Starts Claude Code in background and returns a response_id.
    Client polls /api/chat/poll/<response_id> for updates.
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id')
        ticket = data.get('ticket')
        client = data.get('client')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        user = g.user.get('preferred_username', 'unknown')
        logger.info(f"Chat message from {user}: {message[:100]}")

        # Build context for Claude
        context = build_context(ticket, client, user)

        # Get or create Claude session
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                session_id = session_manager.create_session(user, context)
                session = session_manager.get_session(session_id)
        else:
            session_id = session_manager.create_session(user, context)
            session = session_manager.get_session(session_id)

        if not session:
            return jsonify({'error': 'Failed to create session'}), 500

        # Generate unique response ID
        response_id = str(uuid.uuid4())

        # Initialize response buffer
        response_buffers[response_id] = {
            'chunks': [],
            'done': False,
            'error': None,
            'session_id': session_id
        }

        # Start background thread to collect response
        import threading
        def collect_response():
            try:
                logger.info(f"Starting to collect response for {response_id}")
                chunk_count = 0
                for chunk in session.send_message_stream(message):
                    chunk_count += 1
                    try:
                        chunk_data = json.loads(chunk)
                        response_buffers[response_id]['chunks'].append(chunk_data)
                        logger.debug(f"Added chunk {chunk_count} type={chunk_data.get('type')}")
                    except json.JSONDecodeError:
                        response_buffers[response_id]['chunks'].append({'type': 'chunk', 'content': chunk})
                        logger.debug(f"Added text chunk {chunk_count}")

                logger.info(f"Stream complete for {response_id}, collected {chunk_count} chunks")
                response_buffers[response_id]['done'] = True
            except Exception as e:
                logger.error(f"Error collecting response: {e}", exc_info=True)
                response_buffers[response_id]['error'] = str(e)
                response_buffers[response_id]['done'] = True

        thread = threading.Thread(target=collect_response, daemon=True)
        thread.start()

        return jsonify({
            'response_id': response_id,
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/poll/<response_id>', methods=['GET'])
@token_required
def poll_response(response_id):
    """Poll for new chunks from a running Claude Code response."""

    if response_id not in response_buffers:
        return jsonify({'error': 'Invalid response ID'}), 404

    buffer = response_buffers[response_id]

    # Get the offset parameter (how many chunks client already has)
    offset = int(request.args.get('offset', 0))

    # Return new chunks since offset
    new_chunks = buffer['chunks'][offset:]

    response = {
        'chunks': new_chunks,
        'offset': len(buffer['chunks']),
        'done': buffer['done'],
        'error': buffer['error'],
        'session_id': buffer.get('session_id')
    }

    # Clean up buffer if done and client has received all chunks
    if buffer['done'] and offset >= len(buffer['chunks']):
        del response_buffers[response_id]

    return jsonify(response)


def build_context(ticket: Optional[str], client: Optional[str], user: str) -> Dict:
    """
    Build context information for Claude.

    Args:
        ticket: Current ticket number
        client: Current client name
        user: Current user

    Returns:
        Context dictionary with available data
    """
    context = {
        'user': user,
        'ticket': ticket,
        'client': client,
        'capabilities': [
            'search_knowledge',
            'list_tickets',
            'get_ticket_details',
            'list_devices',
            'get_device_info',
            'list_clients',
            'run_powershell_command'  # With approval
        ]
    }

    # If we have a ticket, fetch its details
    if ticket:
        try:
            # TODO: Call Codex to get ticket details
            context['ticket_details'] = {'status': 'pending'}
        except:
            pass

    # If we have a client, fetch their info
    if client:
        try:
            # TODO: Call Codex to get client details
            context['client_details'] = {'name': client}
        except:
            pass

    return context


def create_command_request(command: str, device_id: str, reason: str) -> Dict:
    """
    Create a pending command that needs approval.

    Args:
        command: PowerShell command to run
        device_id: Target device ID
        reason: Reason for running command

    Returns:
        Command request dict
    """
    command_id = str(uuid.uuid4())

    pending_commands[command_id] = {
        'id': command_id,
        'command': command,
        'device_id': device_id,
        'reason': reason,
        'status': 'pending',
        'created_at': None  # TODO: Add timestamp
    }

    return {
        'id': command_id,
        'device_id': device_id,
        'command': command,
        'reason': reason
    }


@app.route('/api/chat/command/approve', methods=['POST'])
@token_required
def approve_command():
    """
    Approve and execute a pending command.

    Request body:
    {
        "command_id": "uuid"
    }

    Response:
    {
        "status": "success",
        "output": "command output"
    }
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        command_id = data.get('command_id')

        if not command_id or command_id not in pending_commands:
            return jsonify({'error': 'Invalid command ID'}), 404

        command = pending_commands[command_id]

        # Log the approval
        user = g.user.get('preferred_username', 'unknown')
        logger.info(f"User {user} approved command {command_id}: {command['command']}")

        # Execute the command
        # TODO: Implement actual remote execution via Datto RMM
        output = execute_remote_command(command['device_id'], command['command'])

        # Update command status
        command['status'] = 'executed'
        command['executed_by'] = user
        command['output'] = output

        return jsonify({
            'status': 'success',
            'output': output
        })

    except Exception as e:
        logger.error(f"Command approval error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/command/deny', methods=['POST'])
@token_required
def deny_command():
    """
    Deny a pending command.

    Request body:
    {
        "command_id": "uuid"
    }
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        command_id = data.get('command_id')

        if not command_id or command_id not in pending_commands:
            return jsonify({'error': 'Invalid command ID'}), 404

        command = pending_commands[command_id]

        # Log the denial
        user = g.user.get('preferred_username', 'unknown')
        logger.info(f"User {user} denied command {command_id}")

        # Update command status
        command['status'] = 'denied'
        command['denied_by'] = user

        # Remove from pending
        del pending_commands[command_id]

        return jsonify({'status': 'denied'})

    except Exception as e:
        logger.error(f"Command denial error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def execute_remote_command(device_id: str, command: str) -> str:
    """
    Execute a PowerShell command on a remote device.

    This is a placeholder. In production, this would integrate with
    Datto RMM or another remote management tool.

    Args:
        device_id: Target device ID
        command: PowerShell command to run

    Returns:
        Command output
    """
    # TODO: Implement actual Datto RMM integration
    # For now, return simulated output

    logger = get_helm_logger()
    logger.info(f"Simulated command execution on device {device_id}: {command}")

    return f"""Simulated output for: {command}

Device ID       : {device_id}
CsName          : WORKSTATION-001
WindowsVersion  : 10.0.19045
OsArchitecture  : 64-bit

(This is simulated output. Actual Datto RMM integration needed.)"""


@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
@token_required
def destroy_session(session_id: str):
    """
    Destroy a Claude Code session.

    Used when the user closes the chat or logs out.
    """
    logger = get_helm_logger()

    try:
        session_manager.destroy_session(session_id)
        logger.info(f"Destroyed session {session_id}")
        return jsonify({'status': 'destroyed'})
    except Exception as e:
        logger.error(f"Error destroying session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/command/<command_id>/status', methods=['GET'])
@token_required
def get_command_status(command_id: str):
    """
    Get the status of a command execution.

    This is called from the datto_tools.get_command_status() function.
    """
    logger = get_helm_logger()

    try:
        command = pending_commands.get(command_id)

        if not command:
            return jsonify({
                'error': 'Command not found',
                'command_id': command_id,
                'status': 'unknown'
            }), 404

        return jsonify({
            'command_id': command_id,
            'status': command.get('status'),
            'device_id': command.get('device_id'),
            'command': command.get('command'),
            'reason': command.get('reason'),
            'executed_by': command.get('executed_by'),
            'denied_by': command.get('denied_by'),
            'output': command.get('output')
        })

    except Exception as e:
        logger.error(f"Error getting command status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
