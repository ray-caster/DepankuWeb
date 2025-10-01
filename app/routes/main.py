import os
import logging
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Renders the main landing page."""
    algolia_app_id = os.environ.get('ALGOLIA_APP_ID', '')
    # IMPORTANT: Use a SEARCH-ONLY API key on the frontend for security
    algolia_search_key = os.environ.get('ALGOLIA_SEARCH_KEY', '')
    
    logger.info(f"Passing Algolia credentials to template - App ID: {'***' if algolia_app_id else 'Not set'}")
    
    return render_template('index.html',
                           ALGOLIA_APP_ID=algolia_app_id,
                           ALGOLIA_API_KEY=algolia_search_key)

# FIX: Added route to serve the login page
@main_bp.route('/login')
def login_page():
    """Renders the login page."""
    return render_template('login.html')

# FIX: Added route to serve the signup page
@main_bp.route('/signup')
def signup_page():
    """Renders the signup page."""
    return render_template('signup.html')