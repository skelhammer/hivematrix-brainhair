"""
Brain Hair API Routes

This module provides AI-accessible API endpoints that expose data from various
HiveMatrix services and external systems (FreshService, Datto) with automatic
PHI/CJIS filtering via Presidio.
"""

from flask import render_template, g, jsonify, request
from app import app, limiter
from .auth import token_required, allow_localhost
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


@app.route('/history')
@token_required
def history_page():
    """
    Renders the chat history page.
    """
    logger = get_helm_logger()

    if g.is_service_call:
        logger.warning(f"Service {g.service} attempted to access user-only endpoint /history")
        return jsonify({
            'error': 'This endpoint is for users only',
            'service': g.service
        }), 403

    user = g.user
    logger.info(f"User {user.get('preferred_username')} accessed chat history page")

    return render_template('history.html', user=user)


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

            # Handle both dict and list responses
            if isinstance(data, dict):
                result_count = len(data.get('results', []))
            elif isinstance(data, list):
                result_count = len(data)
            else:
                result_count = 'unknown'
            logger.info(f"Knowledge search completed: query='{query}', results={result_count}")

            return jsonify({
                'query': query,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"KnowledgeTree search failed: {response.status_code}")
            return jsonify({'error': 'KnowledgeTree search failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling KnowledgeTree: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
        # Call KnowledgeTree service API endpoint
        endpoint = f'/api/browse?path=/{path}' if path else '/api/browse?path=/'
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
        logger.error(f"Error calling KnowledgeTree: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
        logger.error(f"Error calling KnowledgeTree: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


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
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/codex/contacts', methods=['GET'])
@token_required
def codex_contacts():
    """
    Get contacts from Codex with filtering.

    Query params:
        company_id: Filter by company ID (optional)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    company_id = request.args.get('company_id')
    filter_type = request.args.get('filter', 'phi')

    try:
        # Build endpoint
        endpoint = '/api/contacts'
        if company_id:
            endpoint += f'?company_id={company_id}'

        # Call Codex service
        response = call_service('codex', endpoint)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex contacts retrieved: count={len(filtered_data) if isinstance(filtered_data, list) else 'N/A'}")

            return jsonify({
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex contacts retrieval failed: {response.status_code}")
            return jsonify({'error': 'Contacts retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/codex/contact/<int:contact_id>', methods=['GET'])
@token_required
def codex_contact(contact_id: int):
    """
    Get a specific contact from Codex with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/contact/{contact_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex contact retrieved: contact_id={contact_id}")

            return jsonify({
                'contact_id': contact_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex contact retrieval failed: {response.status_code}")
            return jsonify({'error': 'Contact not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/codex/assets', methods=['GET'])
@token_required
def codex_assets():
    """
    Get assets from Codex with filtering.

    Query params:
        company_id: Filter by company ID (optional)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    company_id = request.args.get('company_id')
    filter_type = request.args.get('filter', 'phi')

    try:
        # Build endpoint
        endpoint = '/api/assets'
        if company_id:
            endpoint += f'?company_id={company_id}'

        # Call Codex service
        response = call_service('codex', endpoint)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex assets retrieved: count={len(filtered_data) if isinstance(filtered_data, list) else 'N/A'}")

            return jsonify({
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex assets retrieval failed: {response.status_code}")
            return jsonify({'error': 'Assets retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/codex/asset/<int:asset_id>', methods=['GET'])
@token_required
def codex_asset(asset_id: int):
    """
    Get a specific asset from Codex with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/asset/{asset_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex asset retrieved: asset_id={asset_id}")

            return jsonify({
                'asset_id': asset_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex asset retrieval failed: {response.status_code}")
            return jsonify({'error': 'Asset not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Codex Ticket Integration ====================

@app.route('/api/codex/ticket/<int:ticket_id>', methods=['GET'])
@token_required
def codex_ticket(ticket_id: int):
    """
    Get a specific ticket from Codex with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Codex service
        response = call_service('codex', f'/api/ticket/{ticket_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Codex ticket retrieved: ticket_id={ticket_id}")

            return jsonify({
                'source': 'codex',
                'ticket_id': ticket_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Codex ticket retrieval failed: {response.status_code}")
            return jsonify({'error': 'Ticket not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Codex: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Beacon Integration ====================

@app.route('/api/beacon/tickets', methods=['GET'])
@token_required
def beacon_tickets():
    """
    Get tickets from Beacon dashboard with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
        status: Optional status filter
        limit: Number of results to return (optional)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')
    status = request.args.get('status')
    limit = request.args.get('limit', '50')

    try:
        # Build query parameters
        params = {'limit': limit}
        if status:
            params['status'] = status

        # Call Beacon service
        response = call_service('beacon', '/api/tickets', params=params)

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Beacon tickets retrieved: count={len(filtered_data) if isinstance(filtered_data, list) else 'N/A'}")

            return jsonify({
                'source': 'beacon',
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Beacon tickets retrieval failed: {response.status_code}")
            return jsonify({'error': 'Beacon tickets retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Beacon: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/beacon/ticket/<int:ticket_id>', methods=['GET'])
@token_required
def beacon_ticket(ticket_id: int):
    """
    Get a specific ticket from Beacon with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Beacon service
        response = call_service('beacon', f'/api/ticket/{ticket_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Beacon ticket retrieved: ticket_id={ticket_id}")

            return jsonify({
                'source': 'beacon',
                'ticket_id': ticket_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Beacon ticket retrieval failed: {response.status_code}")
            return jsonify({'error': 'Ticket not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Beacon: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/beacon/dashboard', methods=['GET'])
@token_required
def beacon_dashboard():
    """
    Get dashboard data from Beacon with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Beacon service
        response = call_service('beacon', '/api/dashboard')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info("Beacon dashboard retrieved")

            return jsonify({
                'source': 'beacon',
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Beacon dashboard retrieval failed: {response.status_code}")
            return jsonify({'error': 'Dashboard retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Beacon: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Archive Integration ====================

@app.route('/api/archive/search', methods=['GET'])
@token_required
def archive_search():
    """
    Search archived data with filtering.

    Query params:
        q: Search query
        filter: Filter type ("phi", "cjis", or none for PHI)
        limit: Number of results to return (optional)
    """
    logger = get_helm_logger()

    query = request.args.get('q', '')
    filter_type = request.args.get('filter', 'phi')
    limit = request.args.get('limit', '50')

    try:
        # Call Archive service
        response = call_service('archive', '/api/search', params={'q': query, 'limit': limit})

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Archive search completed: query='{query}'")

            return jsonify({
                'source': 'archive',
                'query': query,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Archive search failed: {response.status_code}")
            return jsonify({'error': 'Archive search failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Archive: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/archive/items', methods=['GET'])
@token_required
def archive_items():
    """
    List archived items with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
        limit: Number of results to return (optional)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')
    limit = request.args.get('limit', '50')

    try:
        # Call Archive service
        response = call_service('archive', '/api/items', params={'limit': limit})

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Archive items retrieved: count={len(filtered_data) if isinstance(filtered_data, list) else 'N/A'}")

            return jsonify({
                'source': 'archive',
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Archive items retrieval failed: {response.status_code}")
            return jsonify({'error': 'Archive items retrieval failed'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Archive: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/archive/item/<int:item_id>', methods=['GET'])
@token_required
def archive_item(item_id: int):
    """
    Get a specific archived item with filtering.

    Query params:
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    filter_type = request.args.get('filter', 'phi')

    try:
        # Call Archive service
        response = call_service('archive', f'/api/item/{item_id}')

        if response.status_code == 200:
            data = response.json()

            # Apply Presidio filtering
            filtered_data = apply_filter(data, filter_type)

            logger.info(f"Archive item retrieved: item_id={item_id}")

            return jsonify({
                'source': 'archive',
                'item_id': item_id,
                'filter_applied': filter_type,
                'data': filtered_data
            })
        else:
            logger.error(f"Archive item retrieval failed: {response.status_code}")
            return jsonify({'error': 'Item not found'}), response.status_code

    except Exception as e:
        logger.error(f"Error calling Archive: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Ledger Billing Integration ====================

@app.route('/api/ledger/billing/<account_number>', methods=['GET'])
@token_required
def ledger_billing(account_number: str):
    """
    Get billing data for a specific company from Ledger.

    Query params:
        year: Billing year (optional)
        month: Billing month (optional)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    filter_type = request.args.get('filter', 'phi')

    try:
        data = ledger.get_billing_for_client(account_number, year, month)

        if 'error' in data:
            logger.error(f"Ledger billing error for {account_number}: {data['error']}")
            return jsonify(data), 500

        # Apply filtering
        filtered_data = apply_filter(data, filter_type)

        logger.info(f"Retrieved billing data for {account_number}")
        return jsonify({
            'account_number': account_number,
            'filter_applied': filter_type,
            'data': filtered_data
        })

    except Exception as e:
        logger.error(f"Error fetching billing data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/dashboard', methods=['GET'])
@token_required
def ledger_dashboard():
    """
    Get billing dashboard for all companies.

    Query params:
        year: Billing year (optional)
        month: Billing month (optional)
        filter: Filter type ("phi", "cjis", or none for PHI)
    """
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    filter_type = request.args.get('filter', 'phi')

    try:
        data = ledger.get_billing_dashboard(year, month)

        if 'error' in data:
            return jsonify(data), 500

        # Apply filtering
        filtered_data = apply_filter(data, filter_type)

        logger.info("Retrieved billing dashboard")
        return jsonify({
            'filter_applied': filter_type,
            'data': filtered_data
        })

    except Exception as e:
        logger.error(f"Error fetching dashboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/plans', methods=['GET'])
@token_required
def ledger_plans():
    """Get all available billing plans from Ledger."""
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        plans = ledger.get_billing_plans()
        logger.info(f"Retrieved {len(plans)} billing plans")
        return jsonify({'plans': plans})

    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/overrides/client/<account_number>', methods=['GET'])
@token_required
def get_client_overrides(account_number: str):
    """Get billing overrides for a specific client."""
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        data = ledger.get_client_overrides(account_number)
        logger.info(f"Retrieved overrides for {account_number}")
        return jsonify(data)

    except Exception as e:
        logger.error(f"Error fetching overrides: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/overrides/client/<account_number>', methods=['PUT', 'POST'])
@token_required
def set_client_overrides(account_number: str):
    """
    Set or update billing overrides for a client.

    Request body (all fields optional):
    {
        "billing_plan": "Premium Support",
        "support_level": "All Inclusive",
        "per_user_cost": 15.00,
        "per_workstation_cost": 75.00,
        "per_server_cost": 150.00,
        "per_vm_cost": 100.00,
        "per_switch_cost": 50.00,
        "per_firewall_cost": 75.00,
        "per_hour_ticket_cost": 150.00,
        "prepaid_hours_monthly": 4.0,
        "prepaid_hours_yearly": 48.0
    }
    """
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = ledger.set_client_override(account_number, data)
        logger.info(f"Updated overrides for {account_number}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error setting overrides: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/overrides/client/<account_number>', methods=['DELETE'])
@token_required
def delete_client_overrides_route(account_number: str):
    """Remove all billing overrides for a client."""
    logger = get_helm_logger()

    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        result = ledger.delete_client_overrides(account_number)
        logger.info(f"Deleted overrides for {account_number}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error deleting overrides: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-assets/<account_number>', methods=['GET'])
@token_required
def get_manual_assets(account_number: str):
    """Get manual assets for a company."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        assets = ledger.get_manual_assets(account_number)
        return jsonify({'manual_assets': assets})
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-assets/<account_number>', methods=['POST'])
@token_required
def add_manual_asset(account_number: str):
    """
    Add a manual asset for a company.

    Request body:
    {
        "hostname": "server01",
        "billing_type": "Server",
        "custom_cost": 150.00,  // optional
        "notes": "Legacy server"  // optional
    }
    """
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data or 'hostname' not in data or 'billing_type' not in data:
        return jsonify({'error': 'hostname and billing_type required'}), 400

    try:
        result = ledger.add_manual_asset(
            account_number,
            data['hostname'],
            data['billing_type'],
            data.get('custom_cost'),
            data.get('notes')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-assets/<account_number>/<int:asset_id>', methods=['DELETE'])
@token_required
def delete_manual_asset(account_number: str, asset_id: int):
    """Delete a manual asset."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        result = ledger.delete_manual_asset(account_number, asset_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-users/<account_number>', methods=['GET'])
@token_required
def get_manual_users(account_number: str):
    """Get manual users for a company."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        users = ledger.get_manual_users(account_number)
        return jsonify({'manual_users': users})
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-users/<account_number>', methods=['POST'])
@token_required
def add_manual_user(account_number: str):
    """
    Add a manual user for a company.

    Request body:
    {
        "full_name": "John Doe",
        "billing_type": "Paid",
        "custom_cost": 15.00,  // optional
        "notes": "Executive user"  // optional
    }
    """
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data or 'full_name' not in data or 'billing_type' not in data:
        return jsonify({'error': 'full_name and billing_type required'}), 400

    try:
        result = ledger.add_manual_user(
            account_number,
            data['full_name'],
            data['billing_type'],
            data.get('custom_cost'),
            data.get('notes')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/manual-users/<account_number>/<int:user_id>', methods=['DELETE'])
@token_required
def delete_manual_user(account_number: str, user_id: int):
    """Delete a manual user."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        result = ledger.delete_manual_user(account_number, user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/line-items/<account_number>', methods=['GET'])
@token_required
def get_line_items(account_number: str):
    """Get custom line items for a company."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        items = ledger.get_custom_line_items(account_number)
        return jsonify({'line_items': items})
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/line-items/<account_number>', methods=['POST'])
@token_required
def add_line_item(account_number: str):
    """
    Add a custom line item for a company.

    Request body:
    {
        "name": "Office 365 Licenses",
        "description": "Monthly subscription",  // optional
        "monthly_fee": 500.00,  // optional - for recurring monthly
        "one_off_fee": 1000.00,  // optional - for one-time charge
        "one_off_year": 2025,  // required if one_off_fee set
        "one_off_month": 10,  // required if one_off_fee set
        "yearly_fee": 5000.00,  // optional - for annual charge
        "yearly_bill_month": 1  // required if yearly_fee set (1-12)
    }
    """
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({'error': 'name required'}), 400

    try:
        result = ledger.add_custom_line_item(account_number, **data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/line-items/<account_number>/<int:item_id>', methods=['PUT'])
@token_required
def update_line_item(account_number: str, item_id: int):
    """Update a custom line item (same fields as POST)."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        result = ledger.update_custom_line_item(account_number, item_id, **data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/line-items/<account_number>/<int:item_id>', methods=['DELETE'])
@token_required
def delete_line_item(account_number: str, item_id: int):
    """Delete a custom line item."""
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    try:
        result = ledger.delete_custom_line_item(account_number, item_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/invoice/<account_number>/summary', methods=['GET'])
@token_required
def get_invoice_summary(account_number: str):
    """
    Get invoice summary for a specific period.

    Query params:
        year: Invoice year (required)
        month: Invoice month (required)
    """
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'error': 'year and month required'}), 400

    try:
        result = ledger.get_invoice_summary(account_number, year, month)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/ledger/bill/accept', methods=['POST'])
@token_required
def accept_bill():
    """
    Accept and archive a bill.

    Request body:
    {
        "account_number": "123456",
        "year": 2025,
        "month": 10,
        "notes": "Approved by manager"  // optional
    }
    """
    from .ledger_client import get_ledger_client
    ledger = get_ledger_client()

    data = request.get_json()

    if not data or 'account_number' not in data or 'year' not in data or 'month' not in data:
        return jsonify({'error': 'account_number, year, and month required'}), 400

    try:
        result = ledger.accept_bill(
            data['account_number'],
            data['year'],
            data['month'],
            data.get('notes')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Contract Alignment Tool ====================

@app.route('/api/contract/analyze', methods=['POST'])
@token_required
def analyze_contract():
    """
    Analyze a contract and prepare for alignment.

    Request body:
    {
        "account_number": "123456",
        "contract_text": "Full contract text or excerpts..."
    }

    Returns current settings and recommendations.
    """
    logger = get_helm_logger()

    from .contract_alignment import get_contract_alignment_tool
    tool = get_contract_alignment_tool()

    data = request.get_json()

    if not data or 'account_number' not in data or 'contract_text' not in data:
        return jsonify({'error': 'account_number and contract_text required'}), 400

    try:
        result = tool.analyze_contract(data['contract_text'], data['account_number'])
        logger.info(f"Analyzed contract for {data['account_number']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error analyzing contract: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/contract/current-settings/<account_number>', methods=['GET'])
@token_required
def get_current_billing_settings(account_number: str):
    """
    Get comprehensive current billing settings for a company.

    Includes billing data, overrides, manual items, line items, etc.
    """
    logger = get_helm_logger()

    from .contract_alignment import get_contract_alignment_tool
    tool = get_contract_alignment_tool()

    try:
        result = tool.get_current_settings(account_number)
        logger.info(f"Retrieved current settings for {account_number}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/contract/compare', methods=['POST'])
@token_required
def compare_contract_to_settings():
    """
    Compare extracted contract terms with current billing settings.

    Request body:
    {
        "account_number": "123456",
        "contract_terms": {
            "billing_method": "per_user",
            "per_user_rate": 15.00,
            "hourly_rate": 150.00,
            "prepaid_hours_monthly": 4.0,
            "support_level": "All Inclusive"
        }
    }

    Returns comparison report with discrepancies and recommendations.
    """
    logger = get_helm_logger()

    from .contract_alignment import get_contract_alignment_tool
    tool = get_contract_alignment_tool()

    data = request.get_json()

    if not data or 'account_number' not in data or 'contract_terms' not in data:
        return jsonify({'error': 'account_number and contract_terms required'}), 400

    try:
        result = tool.compare_contract_to_settings(data['account_number'], data['contract_terms'])
        logger.info(f"Compared contract terms for {data['account_number']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error comparing terms: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/contract/align', methods=['POST'])
@token_required
def align_billing_settings():
    """
    Align billing settings with contract terms.

    Request body:
    {
        "account_number": "123456",
        "adjustments": {
            "per_user_cost": 15.00,
            "per_hour_ticket_cost": 150.00,
            "prepaid_hours_monthly": 4.0,
            "support_level": "All Inclusive",
            "add_line_items": [
                {
                    "name": "Flat Fee Adjustment",
                    "monthly_fee": 1000.00
                }
            ]
        },
        "dry_run": true  // Set to false to actually apply changes
    }

    Returns results of alignment operation.
    """
    logger = get_helm_logger()

    from .contract_alignment import get_contract_alignment_tool
    tool = get_contract_alignment_tool()

    data = request.get_json()

    if not data or 'account_number' not in data or 'adjustments' not in data:
        return jsonify({'error': 'account_number and adjustments required'}), 400

    dry_run = data.get('dry_run', True)

    try:
        result = tool.align_settings(data['account_number'], data['adjustments'], dry_run)

        if not dry_run:
            logger.info(f"Applied alignment for {data['account_number']}")
        else:
            logger.info(f"Dry run alignment for {data['account_number']}")

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error aligning settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/contract/verify', methods=['POST'])
@token_required
def verify_alignment():
    """
    Verify that billing settings match contract terms.

    Request body:
    {
        "account_number": "123456",
        "contract_terms": {
            "per_user_rate": 15.00,
            "hourly_rate": 150.00,
            ...
        }
    }

    Returns verification report.
    """
    logger = get_helm_logger()

    from .contract_alignment import get_contract_alignment_tool
    tool = get_contract_alignment_tool()

    data = request.get_json()

    if not data or 'account_number' not in data or 'contract_terms' not in data:
        return jsonify({'error': 'account_number and contract_terms required'}), 400

    try:
        result = tool.verify_alignment(data['account_number'], data['contract_terms'])
        logger.info(f"Verified alignment for {data['account_number']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error verifying alignment: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ==================== Utility Endpoints ====================

@app.route('/api/health', methods=['GET'])
@token_required
@limiter.exempt
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'brainhair',
        'version': '1.0.0'
    })


@app.route('/health', methods=['GET'])
@limiter.exempt
def public_health():
    """Public health check endpoint (no auth required)."""
    return jsonify({
        'status': 'healthy',
        'service': 'brainhair'
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
        'psa': {
            '/api/psa/tickets': 'List PSA tickets',
            '/api/psa/ticket/<id>': 'Get specific ticket'
        },
        'datto': {
            '/api/datto/devices': 'List Datto devices',
            '/api/datto/device/<id>': 'Get specific device'
        },
        'ledger': {
            '/api/ledger/billing/<account_number>': 'Get billing data for company',
            '/api/ledger/dashboard': 'Get billing dashboard for all companies',
            '/api/ledger/plans': 'List all billing plans',
            '/api/ledger/overrides/client/<account_number>': 'Get/set/delete client billing overrides',
            '/api/ledger/manual-assets/<account_number>': 'Get/add manual assets',
            '/api/ledger/manual-users/<account_number>': 'Get/add manual users',
            '/api/ledger/line-items/<account_number>': 'Get/add/update/delete custom line items',
            '/api/ledger/invoice/<account_number>/summary': 'Get invoice summary',
            '/api/ledger/bill/accept': 'Accept and archive a bill'
        },
        'contract_alignment': {
            '/api/contract/analyze': 'Analyze a contract and load current settings',
            '/api/contract/current-settings/<account_number>': 'Get comprehensive current billing settings',
            '/api/contract/compare': 'Compare contract terms with current settings',
            '/api/contract/align': 'Align billing settings to match contract (dry_run supported)',
            '/api/contract/verify': 'Verify alignment between contract and settings'
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
