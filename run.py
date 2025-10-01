# --- run.py (MODIFIED) ---
import os
from app import create_app
from dotenv import load_dotenv

load_dotenv()

# Get environment, default to 'development'
env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    # This is for local development only.
    # For production, use a proper WSGI/ASGI server like Gunicorn + Uvicorn.
    # Example command:
    # gunicorn --workers 4 --bind 0.0.0.0:6000 "run:app"
    # Or for async:
    # gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:6000 "run:app"
    
    port = int(os.environ.get('PORT', 6000))
    # Debug mode is now handled by the config object
    app.run(port=port, host='0.0.0.0')