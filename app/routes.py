from flask import render_template, g
from app import app
from .auth import token_required

@app.route('/')
@token_required
def index():
    """
    Renders the main page of the template app.
    This route is now protected and requires a valid JWT.
    """
    # The user object is available from the g context, set by the decorator
    user = g.user
    return render_template('index.html', user=user)
