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

# Store pending approval requests
# Structure: {approval_id: {'session_id': str, 'action': str, 'details': dict, 'status': 'pending'|'approved'|'denied', 'result': any}}
pending_approvals = {}

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
        db_session_id = data.get('db_session_id')  # Database session ID for resuming
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
                session_id = session_manager.create_session(user, context, db_session_id=db_session_id)
                session = session_manager.get_session(session_id)
        else:
            session_id = session_manager.create_session(user, context, db_session_id=db_session_id)
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
        from flask import copy_current_request_context

        @copy_current_request_context
        def collect_response():
            try:
                logger.info(f"Starting to collect response for {response_id}")
                chunk_count = 0
                for chunk in session.send_message_stream(message):
                    chunk_count += 1
                    try:
                        chunk_data = json.loads(chunk)
                        response_buffers[response_id]['chunks'].append(chunk_data)
                        chunk_type = chunk_data.get('type') if isinstance(chunk_data, dict) else str(type(chunk_data))
                        logger.debug(f"Added chunk {chunk_count} type={chunk_type}")
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
    import glob

    if response_id not in response_buffers:
        return jsonify({'error': 'Invalid response ID'}), 404

    buffer = response_buffers[response_id]
    session_id = buffer.get('session_id')

    # Check for approval request files and inject them into the stream
    if session_id:
        approval_files = glob.glob(f"/tmp/brainhair_approval_request_{session_id}_*.json")
        for approval_file in approval_files:
            try:
                with open(approval_file, 'r') as f:
                    approval_data = json.load(f)

                # Add to buffer if not already added
                if not any(chunk.get('approval_id') == approval_data.get('approval_id') for chunk in buffer['chunks']):
                    buffer['chunks'].append(approval_data)
                    logger = get_helm_logger()
                    logger.info(f"Injected approval request into stream: {approval_data.get('approval_id')}")
            except Exception as e:
                logger = get_helm_logger()
                logger.error(f"Error reading approval file {approval_file}: {e}")

    # Get the offset parameter (how many chunks client already has)
    offset = int(request.args.get('offset', 0))

    # Return new chunks since offset
    new_chunks = buffer['chunks'][offset:]

    response = {
        'chunks': new_chunks,
        'offset': len(buffer['chunks']),
        'done': buffer['done'],
        'error': buffer['error'],
        'session_id': session_id
    }

    # Clean up buffer if done and client has received all chunks
    if buffer['done'] and offset >= len(buffer['chunks']):
        del response_buffers[response_id]

    return jsonify(response)


@app.route('/api/chat/stop/<response_id>', methods=['POST'])
@token_required
def stop_response(response_id):
    """Stop a running Claude Code response."""
    from app.chat_routes import session_manager

    logger = get_helm_logger()

    try:
        # Check if response exists
        if response_id not in response_buffers:
            return jsonify({'error': 'Invalid response ID'}), 404

        buffer = response_buffers[response_id]
        session_id = buffer.get('session_id')

        if not session_id:
            return jsonify({'error': 'No session found for this response'}), 404

        # Get the session and stop the current process
        session = session_manager.get_session(session_id)
        if session:
            stopped = session.stop_current_response()
            if stopped:
                # Mark the response as done with a stop message
                buffer['chunks'].append({
                    'type': 'chunk',
                    'content': '\n\n_Response stopped by user._'
                })
                buffer['done'] = True
                logger.info(f"Stopped response {response_id} for session {session_id}")
                return jsonify({'success': True, 'message': 'Response stopped'})
            else:
                return jsonify({'success': False, 'message': 'No active process to stop'}), 400
        else:
            return jsonify({'error': 'Session not found'}), 404

    except Exception as e:
        logger.error(f"Error stopping response: {e}", exc_info=True)
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


# ==================== Chat History Endpoints ====================

@app.route('/api/chat/history', methods=['GET'])
@token_required
def list_chat_sessions():
    """
    List chat sessions for the current user.

    Query parameters:
        - ticket: Filter by ticket number
        - client: Filter by client name
        - limit: Number of sessions to return (default 50)
        - offset: Pagination offset (default 0)
    """
    from models import ChatSession as ChatSessionModel

    logger = get_helm_logger()

    try:
        user = g.user
        user_id = user.get('preferred_username')

        # Build query
        query = ChatSessionModel.query.filter_by(user_id=user_id)

        # Apply filters
        ticket = request.args.get('ticket')
        if ticket:
            query = query.filter_by(ticket_number=ticket)

        client = request.args.get('client')
        if client:
            query = query.filter(ChatSessionModel.client_name.ilike(f'%{client}%'))

        # Pagination
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        # Order by most recent first
        query = query.order_by(ChatSessionModel.updated_at.desc())

        # Get total count
        total = query.count()

        # Get sessions
        sessions = query.limit(limit).offset(offset).all()

        logger.info(f"Listed {len(sessions)} chat sessions for user {user_id}")

        return jsonify({
            'sessions': [s.to_dict() for s in sessions],
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/history/<session_id>', methods=['GET'])
@token_required
def get_chat_session(session_id):
    """
    Get a specific chat session with all messages.
    """
    from models import ChatSession as ChatSessionModel

    logger = get_helm_logger()

    try:
        user = g.user
        user_id = user.get('preferred_username')

        # Get session
        session = ChatSessionModel.query.get(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Verify ownership
        if session.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access session {session_id} owned by {session.user_id}")
            return jsonify({'error': 'Access denied'}), 403

        # Get session with messages
        session_dict = session.to_dict()
        session_dict['messages'] = [m.to_dict() for m in session.messages]

        logger.info(f"Retrieved session {session_id} with {len(session.messages)} messages for user {user_id}")

        return jsonify(session_dict)

    except Exception as e:
        logger.error(f"Error getting chat session: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/history/search', methods=['GET'])
@token_required
def search_chat_history():
    """
    Search chat history by keywords.

    Query parameters:
        - q: Search query
        - ticket: Filter by ticket number
        - limit: Number of results (default 20)
    """
    from models import ChatSession as ChatSessionModel, ChatMessage

    logger = get_helm_logger()

    try:
        user = g.user
        user_id = user.get('preferred_username')

        query_text = request.args.get('q', '').strip()
        if not query_text:
            return jsonify({'error': 'Search query required'}), 400

        # Build query - search in session titles, summaries, and message content
        query = ChatSessionModel.query.filter_by(user_id=user_id)

        # Filter by ticket if specified
        ticket = request.args.get('ticket')
        if ticket:
            query = query.filter_by(ticket_number=ticket)

        # Search in title or summary or messages
        from sqlalchemy import or_
        query = query.join(ChatMessage, ChatSessionModel.id == ChatMessage.session_id)
        query = query.filter(
            or_(
                ChatSessionModel.title.ilike(f'%{query_text}%'),
                ChatSessionModel.summary.ilike(f'%{query_text}%'),
                ChatMessage.content.ilike(f'%{query_text}%')
            )
        )

        # Get unique sessions
        query = query.distinct()

        # Limit results
        limit = min(int(request.args.get('limit', 20)), 50)
        sessions = query.limit(limit).all()

        logger.info(f"Found {len(sessions)} sessions matching '{query_text}' for user {user_id}")

        return jsonify({
            'sessions': [s.to_dict() for s in sessions],
            'query': query_text,
            'count': len(sessions)
        })

    except Exception as e:
        logger.error(f"Error searching chat history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>/title', methods=['PUT'])
@token_required
def update_session_title(session_id):
    """
    Update the title of a chat session.

    Body:
        - title: New title for the session
    """
    from models import ChatSession as ChatSessionModel
    from extensions import db

    logger = get_helm_logger()

    try:
        # Get request data
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({'error': 'Title required'}), 400

        title = data['title'].strip()
        if not title:
            return jsonify({'error': 'Title cannot be empty'}), 400

        # Get session
        session = ChatSessionModel.query.get(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Verify ownership (only for user calls, service calls are trusted)
        if not g.is_service_call:
            user = g.user
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401

            user_id = user.get('preferred_username')
            if session.user_id != user_id:
                return jsonify({'error': 'Unauthorized'}), 403

        # Update title
        session.title = title
        db.session.commit()

        logger.info(f"Updated title for session {session_id} to '{title}'")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'title': title
        })

    except Exception as e:
        logger.error(f"Error updating session title: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================
# Approval Flow Endpoints
# ============================================================

@app.route('/api/approval/request', methods=['POST'])
@token_required
def create_approval_request():
    """
    Create an approval request (called by tools).

    Body:
        - session_id: Session ID
        - action: Description of the action (e.g., "Update billing")
        - details: Dict with details to show user
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        session_id = data.get('session_id')
        action = data.get('action')
        details = data.get('details', {})

        if not session_id or not action:
            return jsonify({'error': 'session_id and action required'}), 400

        # Create approval request
        approval_id = str(uuid.uuid4())
        pending_approvals[approval_id] = {
            'session_id': session_id,
            'action': action,
            'details': details,
            'status': 'pending',
            'result': None
        }

        logger.info(f"Created approval request {approval_id} for session {session_id}: {action}")

        return jsonify({
            'approval_id': approval_id,
            'status': 'pending'
        })

    except Exception as e:
        logger.error(f"Error creating approval request: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/approval/poll/<approval_id>', methods=['GET'])
@token_required
def poll_approval(approval_id):
    """Poll for approval status (called by tools waiting for response)."""
    if approval_id not in pending_approvals:
        return jsonify({'error': 'Invalid approval ID'}), 404

    approval = pending_approvals[approval_id]

    response = {
        'status': approval['status'],
        'result': approval.get('result')
    }

    # Clean up if completed
    if approval['status'] in ['approved', 'denied']:
        del pending_approvals[approval_id]

    return jsonify(response)


@app.route('/api/approval/pending/<session_id>', methods=['GET'])
@token_required
def get_pending_approvals(session_id):
    """Get all pending approvals for a session (called by browser)."""
    pending = [
        {
            'approval_id': aid,
            'action': approval['action'],
            'details': approval['details']
        }
        for aid, approval in pending_approvals.items()
        if approval['session_id'] == session_id and approval['status'] == 'pending'
    ]

    return jsonify({'approvals': pending})


@app.route('/api/approval/respond/<approval_id>', methods=['POST'])
@token_required
def respond_to_approval(approval_id):
    """
    User responds to an approval request.

    Body:
        - approved: true/false
    """
    logger = get_helm_logger()

    try:
        data = request.get_json()
        approved = data.get('approved', False)

        # Write response to file that the tool is polling
        response_file = f"/tmp/brainhair_approval_response_{approval_id}.json"
        with open(response_file, 'w') as f:
            json.dump({'approved': approved}, f)

        logger.info(f"Approval {approval_id} {'approved' if approved else 'denied'} by user")

        return jsonify({
            'success': True,
            'approved': approved
        })

    except Exception as e:
        logger.error(f"Error responding to approval: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
