# HiveMatrix Template Service

This project serves as a barebones template for creating new services within the HiveMatrix ecosystem. It demonstrates how to create a self-contained Flask application that renders its own HTML using the BEM classes defined in the master `ARCHITECTURE.md`.

It contains no CSS and is intended to be run behind the `hivematrix-nexus` proxy, which injects the global stylesheet.

## Running the Service

1.  Create a virtual environment: `python -m venv pyenv`

2.  Activate it: `source pyenv/bin/activate`

3.  Install dependencies: `pip install -r requirements.txt`

4.  Run the app: `flask run --port=5001`


## Setup .flaskenv
```
FLASK_APP=run.py
FLASK_ENV=development
CORE_SERVICE_URL='http://localhost:5000'
SERVICE_NAME='template'
```

The service will be available at `http://localhost:5001`.

## Logging to Helm

HiveMatrix uses the Helm service as the centralized logging aggregator. All services should send their logs to Helm for monitoring, debugging, and analytics.

### Setup

1. Install the HelmLogger client library (already included in requirements.txt):

```python
from helm_logger import HelmLogger

# Initialize the logger
logger = HelmLogger(
    service_name='template',  # Your service name
    helm_url='http://localhost:5004'  # Helm service URL
)
```

2. The logger will automatically retrieve a service token from Core and authenticate with Helm.

### Usage

```python
# Log at different levels
logger.info("Service started successfully")
logger.warning("High memory usage detected", context={'memory_mb': 512})
logger.error("Failed to connect to database", context={'error': str(e)})

# Include trace IDs for request tracking
logger.info("Processing request", trace_id=request_id, user_id=user_email)

# Log with context
logger.info("User action", context={
    'action': 'create_record',
    'record_id': 123,
    'user_id': 'user@example.com'
})
```

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages for potentially harmful situations
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical messages for very serious errors

### Best Practices

1. **Use structured logging**: Always include context as a dictionary rather than in the message string
2. **Include trace IDs**: For request tracking across services, include trace_id
3. **Log user actions**: Include user_id when logging user-initiated actions
4. **Batch logs**: The HelmLogger automatically batches logs every 5 seconds or 50 entries
5. **Don't log sensitive data**: Never log passwords, tokens, or PII
6. **Use appropriate levels**: Don't use ERROR for warnings, or INFO for debug messages

### Viewing Logs

Logs can be viewed in the Helm dashboard:
- Navigate to `http://localhost:8000/helm/` (via Nexus)
- Click on "View All Logs"
- Filter by service name, log level, time range, or trace ID

### Example Integration

```python
from flask import Flask, request, g
from helm_logger import HelmLogger
import uuid

app = Flask(__name__)
logger = HelmLogger(service_name='template', helm_url='http://localhost:5004')

@app.before_request
def before_request():
    # Generate trace ID for this request
    g.trace_id = str(uuid.uuid4())

    # Log the incoming request
    logger.info(f"{request.method} {request.path}",
                trace_id=g.trace_id,
                context={'remote_addr': request.remote_addr})

@app.route('/api/example')
def example_endpoint():
    try:
        # Your logic here
        result = do_something()

        logger.info("Example endpoint success",
                   trace_id=g.trace_id,
                   context={'result_count': len(result)})

        return {'data': result}
    except Exception as e:
        logger.error(f"Example endpoint failed: {str(e)}",
                    trace_id=g.trace_id,
                    context={'error_type': type(e).__name__})
        return {'error': 'Internal server error'}, 500
```

### Configuration

The HelmLogger can be configured with environment variables:

```bash
HELM_SERVICE_URL=http://localhost:5004  # Helm service URL
CORE_SERVICE_URL=http://localhost:5000  # Core service URL for auth
SERVICE_NAME=template                    # Your service name
```

Or in your `.flaskenv`:

```
HELM_SERVICE_URL=http://localhost:5004
CORE_SERVICE_URL=http://localhost:5000
SERVICE_NAME=template
```
