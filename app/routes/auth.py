from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from firebase_admin import auth
from datetime import datetime, timedelta
import logging

from ..extensions import db

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# --- API Endpoints ---
@auth_bp.route('/register', methods=['POST'])
def register():
    """API endpoint for new user registration."""
    try:
        data = request.get_json()
        if not all(k in data for k in ['email', 'password', 'displayName', 'ageGroup']):
            return jsonify({'error': {'code': 'INVALID_REQUEST', 'message': 'Missing required fields'}}), 400

        user = auth.create_user(
            email=data['email'],
            password=data['password'],
            display_name=data['displayName']
        )
        
        user_ref = db.client.collection('users').document(user.uid)
        user_ref.set({
            'uid': user.uid,
            'email': user.email,
            'displayName': data['displayName'],
            'ageGroup': data['ageGroup'],
            'subscription': {
                'plan': 'free',
                'aiAnalysesRemaining': 3,
                'subscriptionDate': datetime.now(),
                'expiryDate': datetime.now() + timedelta(days=30)
            },
            'createdAt': datetime.now(),
            'updatedAt': datetime.now(),
            'lastLogin': datetime.now()
        })
        
        custom_token = auth.create_custom_token(user.uid)
        
        response_data = {
            'uid': user.uid,
            'email': user.email,
            'displayName': data['displayName'],
            'customToken': custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token
        }
        
        # Persist redirect destination if provided
        if data.get('redirectAfterSignup'):
            response_data['redirectAfterSignup'] = data['redirectAfterSignup']
        
        return jsonify({'success': True, 'data': response_data}), 201
        
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        # Provide a more generic error message to the client
        return jsonify({'error': {'code': 'SIGNUP_FAILED', 'message': 'Could not complete registration.'}}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """API endpoint to verify Firebase ID token and create a session."""
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        if not id_token:
            return jsonify({'error': {'code': 'INVALID_REQUEST', 'message': 'ID token is required'}}), 400
        
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        user_ref = db.client.collection('users').document(uid)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'error': {'code': 'USER_NOT_FOUND', 'message': 'User not found in database'}}), 404
        
        user_dict = user_doc.to_dict()
        user_ref.update({'lastLogin': datetime.now()})
        
        # Create a server-side session
        session['user_id'] = uid
        session['user_email'] = user_dict.get('email')
        session['display_name'] = user_dict.get('displayName')
        
        return jsonify({
            'success': True,
            'data': {
                'uid': uid,
                'email': user_dict.get('email'),
                'displayName': user_dict.get('displayName')
            }
        })
        
    except auth.InvalidIdTokenError:
        return jsonify({'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid ID token'}}), 401
    except Exception as e:
        logger.error(f"User login failed: {e}")
        return jsonify({'error': {'code': 'LOGIN_FAILED', 'message': 'Login attempt failed.'}}), 400

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """API endpoint to clear the server-side session."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """API endpoint to get the current user's profile."""
    # SECURITY FIX (IDOR): Use the session ID. Do not allow fetching other users' profiles via query params.
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    try:
        user_ref = db.client.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User profile not found'}}), 404
            
        return jsonify({'success': True, 'data': user_doc.to_dict()})
    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        return jsonify({'error': {'code': 'PROFILE_FETCH_FAILED', 'message': 'Could not retrieve profile.'}}), 500

@auth_bp.route('/check-ai-limit', methods=['GET'])
def check_ai_limit():
    """API endpoint to check the current user's remaining AI analysis credits."""
    # SECURITY FIX (IDOR): Use the session ID. Do not allow checking other users' limits.
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'User ID required'}}), 401
    
    try:
        user_ref = db.client.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'User not found'}}), 404
        
        user_dict = user_doc.to_dict()
        subscription = user_dict.get('subscription', {})
        plan = subscription.get('plan', 'free')
        remaining = subscription.get('aiAnalysesRemaining', 0)
        
        return jsonify({
            'success': True,
            'data': {
                'plan': plan,
                'aiAnalysesRemaining': remaining,
                'hasAccess': plan == 'premium' or remaining > 0
            }
        })
    except Exception as e:
        logger.error(f"Failed to check AI limit for user {user_id}: {e}")
        return jsonify({'error': {'code': 'LIMIT_CHECK_FAILED', 'message': 'Could not check AI limit.'}}), 500