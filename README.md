# HiveMatrix Template Service

This project serves as a barebones template for creating new services within the HiveMatrix ecosystem. It demonstrates how to create a self-contained Flask application that renders its own HTML using the BEM classes defined in the master `ARCHITECTURE.md`.

It contains no CSS and is intended to be run behind the `hivematrix-nexus` proxy, which injects the global stylesheet.

## Running the Service

1.  Create a virtual environment: `python -m venv pyenv`

2.  Activate it: `source pyenv/bin/activate`

3.  Install dependencies: `pip install -r requirements.txt`

4.  Run the app: `flask run --port=5001`


The service will be available at `http://localhost:5001`.
