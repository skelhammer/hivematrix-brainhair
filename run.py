import os
from dotenv import load_dotenv

# Load environment variables from .flaskenv
load_dotenv('.flaskenv')

from app import app

if __name__ == "__main__":
    port = int(os.environ.get('FLASK_RUN_PORT', 5050))
    # Enable threaded mode for proper SSE streaming
    app.run(port=port, host='127.0.0.1', threaded=True)
