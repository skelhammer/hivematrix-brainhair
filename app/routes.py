"""
Brain Hair API Routes

This module provides AI-accessible API endpoints that expose data from various
HiveMatrix services and external systems (FreshService, Datto) with automatic
PHI/CJIS filtering via Presidio.
"""

from flask import render_template, g, jsonify, request
from app import app
from .auth import token_required
from .service_client import call_service
from .helm_logger import get_helm_logger
from .presidio_filter import get_presidio_filter
from typing import Optional, Dict, Any
import json


def apply_filter(data: Any, filter_type: Optional[str] = None) -> Any:
    """
    Apply Presidio filtering to data based on filter type.

    Args:
        data: Data to filter
        filter_type: Type of filter to apply ("phi", "cjis", or None for PHI default)

    Returns:
        Filtered data
    """
    presidio = get_presidio_filter()

    if filter_type == "cjis":
        return presidio.filter_cjis(data)
    else:
        # Default to PHI filtering
        return presidio.filter_phi(data)


@app.route('/')
@token_required
def index():
    """
    Renders the main page of Brain Hair.
    Shows available API endpoints for Claude to use.
    """
    logger = get_helm_logger()

    # Check if this is a service call or user call
    if g.is_service_call:
        logger.warning(f"Service {g.service} attempted to access user-only endpoint /")
        return jsonify({
            'error': 'This endpoint is for users only',
            'service': g.service
        }), 403

    user = g.user
    logger.info(f"User {user.get('preferred_username')} accessed Brain Hair index page")

    # Render a page showing available endpoints
    return render_template('index.html', user=user)


# ==================== KnowledgeTree Integration ====================

@app.route('/api/knowledge/search', methods=['GET'])
@token_required
def knowledge_search():
    """
    Search KnowledgeTree and return filtered results.

    Query params:
        q: Search query
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    query = request.args.get('q', '')
    filter_type = request.args.get('filter', 'phi')

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        # Call KnowledgeTree service
        response = call_service('knowledgetree', f'/api/search?q={query}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Knowledge search completed: query='{query}', results={len(data.get('results', []))}")

            return jsonify({
                'query': query,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"KnowledgeTree search failed: {response.status_code}")
            return jsonify({'error': 'KnowledgeTree search failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling KnowledgeTree: {e}", exc_info=True)
        return jsonify({'error': f'Error calling KnowledgeTree: {str(e)}'}), 500


@app.route('/api/knowledge/browse', methods=['GET'])
@token_required
def knowledge_browse():
    """
    Browse KnowledgeTree nodes and return filtered results.

    Query params:
        path: Path to browse (optional, defaults to root)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    path = request.args.get('path', '')
    filter_type = request.args.get('filter', 'phi')

    try:
        # Call KnowledgeTree service
        endpoint = f'/browse/{path}' if path else '/browse/'
        response = call_service('knowledgetree', endpoint)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Knowledge browse completed: path='{path}'")

            return jsonify({
                'path': path,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"KnowledgeTree browse failed: {response.status_code}")
            return jsonify({'error': 'KnowledgeTree browse failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling KnowledgeTree: {e}", exc_info=True)
        return jsonify({'error': f'Error calling KnowledgeTree: {str(e)}'}), 500


@app.route('/api/knowledge/node/<int:node_id>', methods=['GET'])
@token_required
def knowledge_node(node_id: int):
    """
    Get details of a specific KnowledgeTree node with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call KnowledgeTree service
        response = call_service('knowledgetree', f'/api/node/{node_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Knowledge node retrieved: node_id={node_id}")

            return jsonify({
                'node_id': node_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"KnowledgeTree node retrieval failed: {response.status_code}")
            return jsonify({'error': 'Node not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling KnowledgeTree: {e}", exc_info=True)
        return jsonify({'error': f'Error calling KnowledgeTree: {str(e)}'}), 500


# ==================== Codex Integration ====================

@app.route('/api/codex/companies', methods=['GET'])
@token_required
def codex_companies():
    """
    Get list of companies from Codex with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', '/api/companies')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex companies retrieved: count={len(data) if isinstance(data, list) else 'N/A'}")

            return jsonify({
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex companies retrieval failed: {response.status_code}")
            return jsonify({'error': 'Codex companies retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling Codex: {str(e)}'}), 500


@app.route('/api/codex/company/<int:company_id>', methods=['GET'])
@token_required
def codex_company(company_id: int):
    """
    Get details of a specific company from Codex with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/company/{company_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex company retrieved: company_id={company_id}")

            return jsonify({
                'company_id': company_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex company retrieval failed: {response.status_code}")
            return jsonify({'error': 'Company not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling Codex: {str(e)}'}), 500


@app.route('/api/codex/tickets', methods=['GET'])
@token_required
def codex_tickets():
    """
    Get tickets from Codex with filtering.

    Query params:
        company_id: Filter by company ID (optional)
        status: Filter by status (optional)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    company_id = request.args.get('company_id')
    status = request.args.get('status')
    filter_type = request.args.get('filter', 'phi')

    try:
        # Build query parameters
        params = []
        if company_id:
            params.append(f'company_id={company_id}')
        if status:
            params.append(f'status={status}')

        endpoint = '/api/tickets'
        if params:
            endpoint += '?' + '&'.join(params)

        # Call Codex service
        response = call_service('codex', endpoint)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex tickets retrieved: count={len(data) if isinstance(data, list) else 'N/A'}")

            return jsonify({
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex tickets retrieval failed: {response.status_code}")
            return jsonify({'error': 'Codex tickets retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling Codex: {str(e)}'}), 500


# ==================== FreshService Integration ====================

@app.route('/api/freshservice/tickets', methods=['GET'])
@token_required
def freshservice_tickets():
    """
    Get tickets from FreshService (via Codex sync) with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
        limit: Number of results to return (optional)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')
    limit = request.args.get('limit', '50')

    try:
        # Call Codex service which has FreshService data
        response = call_service('codex', f'/api/freshservice/tickets?limit={limit}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"FreshService tickets retrieved: count={len(data) if isinstance(data, list) else 'N/A'}")

            return jsonify({
                'source': 'freshservice',
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"FreshService tickets retrieval failed: {response.status_code}")
            return jsonify({'error': 'FreshService tickets retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling FreshService via Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling FreshService: {str(e)}'}), 500


@app.route('/api/freshservice/ticket/<int:ticket_id>', methods=['GET'])
@token_required
def freshservice_ticket(ticket_id: int):
    """
    Get a specific ticket from FreshService with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/freshservice/ticket/{ticket_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"FreshService ticket retrieved: ticket_id={ticket_id}")

            return jsonify({
                'source': 'freshservice',
                'ticket_id': ticket_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"FreshService ticket retrieval failed: {response.status_code}")
            return jsonify({'error': 'Ticket not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling FreshService via Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling FreshService: {str(e)}'}), 500


# ==================== Datto Integration ====================

@app.route('/api/datto/devices', methods=['GET'])
@token_required
def datto_devices():
    """
    Get devices from Datto (via Codex sync) with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
        company_id: Filter by company (optional)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')
    company_id = request.args.get('company_id')

    try:
        # Build endpoint
        endpoint = '/api/datto/devices'
        if company_id:
            endpoint += f'?company_id={company_id}'

        # Call Codex service
        response = call_service('codex', endpoint)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Datto devices retrieved: count={len(data) if isinstance(data, list) else 'N/A'}")

            return jsonify({
                'source': 'datto',
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Datto devices retrieval failed: {response.status_code}")
            return jsonify({'error': 'Datto devices retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Datto via Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling Datto: {str(e)}'}), 500


@app.route('/api/datto/device/<device_id>', methods=['GET'])
@token_required
def datto_device(device_id: str):
    """
    Get a specific device from Datto with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/datto/device/{device_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Datto device retrieved: device_id={device_id}")

            return jsonify({
                'source': 'datto',
                'device_id': device_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Datto device retrieval failed: {response.status_code}")
            return jsonify({'error': 'Device not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Datto via Codex: {e}", exc_info=True)
        return jsonify({'error': f'Error calling Datto: {str(e)}'}), 500


# ==================== Utility Endpoints ====================

@app.route('/api/health', methods=['GET'])
@token_required
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'brainhair',
        'version': '1.0.0'
    })


@app.route('/api/endpoints', methods=['GET'])
@token_required
def list_endpoints():
    """
    List all available API endpoints.
    Useful for Claude to discover what tools are available.
    """
    endpoints = {
        'knowledge': {
            '/api/knowledge/search': 'Search KnowledgeTree',
            '/api/knowledge/browse': 'Browse KnowledgeTree nodes',
            '/api/knowledge/node/<id>': 'Get specific node details'
        },
        'codex': {
            '/api/codex/companies': 'List all companies',
            '/api/codex/company/<id>': 'Get company details',
            '/api/codex/tickets': 'List tickets'
        },
        'freshservice': {
            '/api/freshservice/tickets': 'List FreshService tickets',
            '/api/freshservice/ticket/<id>': 'Get specific ticket'
        },
        'datto': {
            '/api/datto/devices': 'List Datto devices',
            '/api/datto/device/<id>': 'Get specific device'
        },
        'utility': {
            '/api/health': 'Health check',
            '/api/endpoints': 'List all endpoints'
        }
    }

    return jsonify({
        'service': 'Brain Hair',
        'description': 'AI-accessible API gateway with automatic PHI/CJIS filtering',
        'endpoints': endpoints,
        'notes': {
            'authentication': 'All endpoints require Bearer token authentication',
            'filtering': 'Add ?filter=phi or ?filter=cjis to any endpoint. Default is PHI filtering.',
            'base_url': 'Access via Nexus: https://your-server/brainhair'
        }
    })
