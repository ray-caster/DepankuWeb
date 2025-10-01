# --- app/__init__.py (MODIFIED) ---
import os
import json
import logging
from flask import Flask
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

from config import config_by_name # MODIFIED: Import config
from .extensions import db, celery # MODIFIED: Import celery instance

def create_app(config_name):
    """Create and configure an instance of the Flask application."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # --- MODIFIED: Configuration from object ---
    config_obj = config_by_name[config_name]
    app.config.from_object(config_obj)
    
    CORS(app)

    # --- Initialize Logging ---
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # --- Initialize Extensions ---
    initialize_firebase(app, logger)
    initialize_celery(app) # NEW

    # --- Register Blueprints ---
    with app.app_context():
        from .routes import main, auth, organizations, ai, dashboard, messaging
        app.register_blueprint(main.main_bp)
        app.register_blueprint(auth.auth_bp, url_prefix='/api/auth')
        app.register_blueprint(organizations.org_bp) 
        app.register_blueprint(ai.ai_bp, url_prefix='/ai')
        app.register_blueprint(dashboard.dashboard_bp, url_prefix='/dashboard')
        app.register_blueprint(messaging.messaging_bp, url_prefix='/messages')

    return app

def initialize_firebase(app, logger):
    """Initializes the Firebase Admin SDK and Firestore client."""
    try:
        if not firebase_admin._apps:
            firebase_config_str = app.config['FIREBASE_SERVICE_ACCOUNT']
            if not firebase_config_str:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable not set or empty.")
            
            logger.info("Loading Firebase service account from config")
            cred_dict = json.loads(firebase_config_str.strip("'"))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        
        db.client = firestore.client()
        logger.info("Firestore client initialized successfully")

    except Exception as e:
        logger.error(f"FATAL: Error initializing Firebase Admin SDK: {e}", exc_info=True)
        raise RuntimeError("Could not initialize Firebase Admin SDK.") from e

def initialize_celery(app):
    """Initializes Celery, linking it to the Flask app configuration."""
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.task_routes = {
        'app.tasks.*': {'queue': 'default'},
    }
    
    # Subclass task to automatically push app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask