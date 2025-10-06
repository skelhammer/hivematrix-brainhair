from flask import render_template, g, jsonify
from app import app
from .auth import token_required
from .service_client import call_service
from .helm_logger import get_helm_logger

@app.route('/')
@token_required
def index():
    """
    Renders the main page of the template app.
    This route is protected and requires a valid JWT.
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
    logger.info(f"User {user.get('preferred_username')} accessed index page")
    return render_template('index.html', user=user)


@app.route('/api/example')
@token_required
def api_example():
    """
    Example API endpoint that can be called by other services.
    """
    logger = get_helm_logger()

    if g.is_service_call:
        logger.info(f"Service {g.service} called /api/example")
        return jsonify({
            'message': 'Hello from Template service!',
            'called_by': g.service,
            'data': {
                'example': 'This is example data',
                'status': 'active'
            }
        })
    else:
        logger.info(f"User {g.user.get('preferred_username')} called /api/example")
        return jsonify({
            'message': 'Hello from Template service!',
            'user': g.user.get('preferred_username'),
            'data': {
                'example': 'This is example data',
                'status': 'active'
            }
        })


@app.route('/demo-service-call')
@token_required
def demo_service_call():
    """
    Demo route showing how to call another service.
    Only accessible to users (not services).
    """
    if g.is_service_call:
        return jsonify({'error': 'Service-to-service calls cannot access this endpoint'}), 403

    try:
        # Example: Call the same service (would normally be a different service)
        response = call_service('template', '/api/example')
        api_data = response.json()

        return render_template('service_call_demo.html',
                             user=g.user,
                             api_response=api_data)
    except Exception as e:
        return f"Error calling service: {str(e)}", 500
