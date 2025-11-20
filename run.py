import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

from app import app

def get_debug_mode():
    """Read environment from master_config.json to determine debug mode"""
    config_path = os.path.join(os.path.dirname(__file__), 'instance', 'master_config.json')
    try:
        with open(config_path) as f:
            config = json.load(f)
            return config.get('system', {}).get('environment', 'production') == 'development'
    except (FileNotFoundError, json.JSONDecodeError):
        return False  # Default to production (debug=False) if config not found

if __name__ == "__main__":
    port = int(os.environ.get('FLASK_RUN_PORT', 5050))
    debug = get_debug_mode()

    # Collect template files for auto-reload in debug mode
    extra_files = []
    if debug:
        templates_dir = Path('app/templates')
        if templates_dir.exists():
            for template_file in templates_dir.rglob('*.html'):
                extra_files.append(str(template_file))

        static_dir = Path('app/static')
        if static_dir.exists():
            for static_file in static_dir.rglob('*'):
                if static_file.is_file():
                    extra_files.append(str(static_file))

    # Security: Bind to localhost only - Brainhair should not be exposed externally
    # Access via Nexus proxy at https://localhost:443/brainhair
    # Enable threaded mode for proper SSE streaming
    app.run(
        port=port,
        host='127.0.0.1',
        threaded=True,
        debug=debug,
        extra_files=extra_files if extra_files else None
    )
