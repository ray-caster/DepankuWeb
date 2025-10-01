# --- celery_worker.py (NEW) ---
import os
from app import create_app, celery

# Create a Flask app instance to configure Celery
# The app context is necessary for tasks to access extensions like the db client
app = create_app(os.getenv('FLASK_ENV') or 'development')
app.app_context().push()