import os
import json
import logging
from flask import Flask
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

from .extensions import db

def create_app():
    """Create and configure an instance of the Flask application."""
    
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # --- Configuration ---
    app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-secret-key-for-development')
    CORS(app)

    # --- Initialize Logging ---
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # --- Initialize Firebase ---
    try:
        if not firebase_admin._apps:
            # MODIFIED: Changed back to read FIREBASE_SERVICE_ACCOUNT directly as requested.
            firebase_config_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
            if firebase_config_str:
                logger.info("Loading Firebase service account from environment variable")
                # The .strip("'") is necessary for .env files that wrap multi-line strings in quotes.
                cred_dict = json.loads(firebase_config_str.strip("'"))
                cred = credentials.Certificate(cred_dict)
            else:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable not set or empty.")
            
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        
        db.client = firestore.client()
        logger.info("Firestore client initialized successfully")

    except Exception as e:
        logger.error(f"FATAL: Error initializing Firebase Admin SDK: {e}")
        # Application cannot run without a database, so we raise an error to stop it.
        raise RuntimeError("Could not initialize Firebase Admin SDK. Application cannot start.") from e

    # --- Register Blueprints ---
    with app.app_context():
        from .routes import main, auth, organizations, ai, dashboard, messaging
        app.register_blueprint(main.main_bp)
        
        # Register other blueprints with their prefixes
        app.register_blueprint(auth.auth_bp, url_prefix='/api/auth')
        app.register_blueprint(organizations.org_bp)
        app.register_blueprint(ai.ai_bp, url_prefix='/ai')
        app.register_blueprint(dashboard.dashboard_bp, url_prefix='/dashboard')
        app.register_blueprint(messaging.messaging_bp, url_prefix='/messages')

    return app