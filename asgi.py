"""
ASGI entry point for Depanku Flask application.
This file provides ASGI compatibility for Uvicorn workers.
"""
import os
import sys
from a2wsgi import ASGIMiddleware

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import app

# Convert Flask WSGI app to ASGI
application = ASGIMiddleware(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=6000)