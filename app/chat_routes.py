"""
Chat routes for Brain Hair AI Assistant

Handles chat interface, Claude API integration, and command approval workflow.
"""

from flask import render_template, request, jsonify, g
from app import app
from .auth import token_required
from .service_client import call_service
from .helm_logger import get_helm_logger
import json
import uuid
from typing import Dict, List, Any, Optional
import os

# Store pending commands (in production, use Redis or database)
pending_commands = {}

# Store chat sessions (in production, use database)
chat_sessions = {}


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


@app.route('/api/chat', methods=['POST'])
@token_required
def chat_message():
    """
    Handle chat messages and route to Claude API.

    Request body:
    {
        "message": "user message",
        "ticket": "ticket number or null",
        "client": "client name or null",
        "history": [{"role": "user/assistant", "content": "..."}]
    }

    Response:
    {
        "response": "assistant response",
        "command_request": {  // Optional, if command approval needed
            "id": "command_id",
            "device": "device name",
            "command": "PowerShell command",
            "reason": "why this command"
        }
    }
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        message = data.get('message', '')
        ticket = data.get('ticket')
        client = data.get('client')
        history = data.get('history', [])

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        user = g.user.get('preferred_username', 'unknown')
        logger.info(f"Chat message from {user}: {message[:100]}")

        # Build context for Claude
        context = build_context(ticket, client, user)

        # Get response from Claude (or simulated for now)
        response = get_claude_response(message, history, context)

        # Check if response includes a command request
        command_request = None
        if response.get('wants_to_run_command'):
            command_request = create_command_request(
                response.get('command'),
                response.get('device'),
                response.get('reason')
            )

        return jsonify({
            'response': response.get('message', 'I apologize, I encountered an error.'),
            'command_request': command_request
        })

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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


def get_claude_response(message: str, history: List[Dict], context: Dict) -> Dict:
    """
    Get response from Claude API.

    For now, this is a placeholder that returns simulated responses.
    In production, this would call the actual Claude API.

    Args:
        message: User's message
        history: Conversation history
        context: Context information

    Returns:
        Response dictionary
    """
    # TODO: Implement actual Claude API integration
    # For now, return a simulated intelligent response

    message_lower = message.lower()

    # Simulate intelligent responses based on keywords
    if 'ticket' in message_lower and 'list' in message_lower:
        return {
            'message': '''I'll help you list recent tickets. Let me query the system.

Based on the current data, here are the most recent tickets:
- #12345: Password reset for John S. (Open)
- #12344: VPN connection issue for Mary J. (In Progress)
- #12343: Printer offline for Robert W. (Resolved)

Would you like me to get more details on any of these tickets?'''
        }

    elif 'knowledge' in message_lower or 'search' in message_lower:
        return {
            'message': '''I can search the knowledge base for you. What specific topic or issue are you looking for?

Some common searches:
- Password reset procedures
- VPN setup guides
- Printer troubleshooting
- Software installation guides

What would you like to search for?'''
        }

    elif 'device' in message_lower or 'computer' in message_lower:
        return {
            'message': f'''I can help with device information.{' For client: ' + context.get('client') if context.get('client') else ''}

I can:
- List all devices for a client
- Check device status and health
- View installed software
- Run diagnostic commands (with your approval)

What would you like to know?'''
        }

    elif 'run' in message_lower or 'command' in message_lower or 'powershell' in message_lower:
        # Simulate a command request
        return {
            'message': 'I can help run commands on devices. What would you like me to do?',
            'wants_to_run_command': True,
            'device': 'WORKSTATION-001',
            'command': 'Get-ComputerInfo | Select-Object CsName, WindowsVersion, OsArchitecture',
            'reason': 'Check system information for troubleshooting'
        }

    elif context.get('ticket'):
        return {
            'message': f'''I'm currently working on ticket #{context.get('ticket')}.

What would you like me to help with for this ticket?
- Search knowledge base for solutions
- Check client's devices
- Review ticket history
- Run diagnostic commands'''
        }

    else:
        return {
            'message': f'''I'm here to help! I can assist with:

📋 **Tickets**: List, search, and manage tickets
📚 **Knowledge Base**: Search documentation and procedures
💻 **Devices**: Check status, run commands (with approval)
🏢 **Clients**: View client information and devices

{f"Currently working on: Ticket #{context.get('ticket')}" if context.get('ticket') else ""}
{f"Currently viewing: {context.get('client')}" if context.get('client') else ""}

What can I help you with?'''
        }


def create_command_request(command: str, device: str, reason: str) -> Dict:
    """
    Create a pending command that needs approval.

    Args:
        command: PowerShell command to run
        device: Target device
        reason: Reason for running command

    Returns:
        Command request dict
    """
    command_id = str(uuid.uuid4())

    pending_commands[command_id] = {
        'id': command_id,
        'command': command,
        'device': device,
        'reason': reason,
        'status': 'pending',
        'created_at': None  # TODO: Add timestamp
    }

    return {
        'id': command_id,
        'device': device,
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
        output = execute_remote_command(command['device'], command['command'])

        # Update command status
        command['status'] = 'executed'
        command['executed_by'] = user

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


def execute_remote_command(device: str, command: str) -> str:
    """
    Execute a PowerShell command on a remote device.

    This is a placeholder. In production, this would integrate with
    Datto RMM or another remote management tool.

    Args:
        device: Target device name
        command: PowerShell command to run

    Returns:
        Command output
    """
    # TODO: Implement actual Datto RMM integration
    # For now, return simulated output

    logger = get_helm_logger()
    logger.info(f"Simulated command execution on {device}: {command}")

    return f"""Simulated output for: {command}

CsName          : {device}
WindowsVersion  : 10.0.19045
OsArchitecture  : 64-bit

(This is simulated output. Actual Datto RMM integration needed.)"""
