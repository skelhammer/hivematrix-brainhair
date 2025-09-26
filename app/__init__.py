from flask import Flask
import os

app = Flask(__name__)

# --- Explicitly load all required configuration from environment variables ---
# This is crucial for the auth decorator to find the Core service.
app.config['CORE_SERVICE_URL'] = os.environ.get('CORE_SERVICE_URL')

if not app.config['CORE_SERVICE_URL']:
    raise ValueError("CORE_SERVICE_URL must be set in the .flaskenv file.")


from app import routes
