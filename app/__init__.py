from flask import Flask
import json
import os

app = Flask(__name__)

# --- Explicitly load all required configuration from environment variables ---
app.config['CORE_SERVICE_URL'] = os.environ.get('CORE_SERVICE_URL')
app.config['SERVICE_NAME'] = os.environ.get('SERVICE_NAME', 'brainhair')
app.config['HELM_SERVICE_URL'] = os.environ.get('HELM_SERVICE_URL', 'http://localhost:5004')

if not app.config['CORE_SERVICE_URL']:
    raise ValueError("CORE_SERVICE_URL must be set in the .flaskenv file.")

# Load services configuration from services.json (for service-to-service calls)
try:
    with open('services.json') as f:
        services_config = json.load(f)
        app.config['SERVICES'] = services_config
except FileNotFoundError:
    print("WARNING: services.json not found. Service-to-service calls will not work.")
    app.config['SERVICES'] = {}

# Initialize Helm logger for centralized logging
from app.helm_logger import init_helm_logger
helm_logger = init_helm_logger(
    app.config['SERVICE_NAME'],
    app.config['HELM_SERVICE_URL']
)

# Download spaCy language model for Presidio if not already installed
try:
    import spacy
    try:
        spacy.load("en_core_web_sm")
    except OSError:
        # Model not found, download it
        helm_logger.info("Downloading spaCy language model en_core_web_sm...")
        from spacy.cli import download
        download("en_core_web_sm")
        helm_logger.info("spaCy model downloaded successfully")
except Exception as e:
    helm_logger.warning(f"Could not download spaCy model: {e}. Presidio may use limited functionality.")

from app import routes
from app import chat_routes

# Log service startup
helm_logger.info(f"{app.config['SERVICE_NAME']} service started")
