# --- run.py (MODIFIED) ---
import os
from app import create_app
from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi # MODIFIED: Import the standard ASGI wrapper

load_dotenv()

# Get environment, default to 'development'
env_name = os.getenv('FLASK_ENV', 'development')

# Create the underlying Flask (WSGI) application
wsgi_app = create_app(env_name)

# MODIFIED: Wrap the WSGI app using the standard `asgiref` library
# This creates a reliable ASGI-compatible application for Gunicorn/Uvicorn.
app = WsgiToAsgi(wsgi_app)


if __name__ == '__main__':
    # This block is for local development only.
    # It uses Flask's built-in development server, which requires the original WSGI app.
    # For production, use a proper ASGI server like Gunicorn + Uvicorn.
    # Example command:
    # gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:6000 "run:app"
    
    port = int(os.environ.get('PORT', 6000))
    # Debug mode is now handled by the config object.
    # Use the original wsgi_app for Flask's development server.
    wsgi_app.run(port=port, host='0.0.0.0')