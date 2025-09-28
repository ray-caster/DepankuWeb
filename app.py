import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Configure logging IMMEDIATELY after loading environment variables
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log Algolia credentials for debugging
algolia_app_id = os.environ.get('ALGOLIA_APP_ID')
algolia_api_key = os.environ.get('ALGOLIA_API_KEY')
logger.info(f"Algolia App ID: {'***' if algolia_app_id else 'Not set'}")
logger.info(f"Algolia API Key: {'***' if algolia_api_key else 'Not set'}")

# Now import other modules (they will use the configured logging)
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timedelta
import json
import asyncio

# Import AI analysis components
from ai_analysis_service import AIAnalysisService
from moderation_service import ModerationService

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# Helper function to normalize tags (ensure they start with '#' and are lowercase)
def normalize_tags(tags):
    """Normalize tags to ensure they start with '#' and are lowercase."""
    normalized = []
    for tag in tags:
        if isinstance(tag, str):
            # Remove any existing '#' and add it back, convert to lowercase
            tag = tag.strip()
            if tag.startswith('#'):
                tag = '#' + tag[1:].lstrip('#')
            else:
                tag = '#' + tag
            normalized.append(tag.lower())
    return normalized

# Initialize Firebase Admin SDK
try:
    # Check if Firebase Admin SDK is already initialized
    if not firebase_admin._apps:
        # Load Firebase service account key from environment variable or file
        firebase_config_str = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        if firebase_config_str:
            logger.info("Loading Firebase service account from environment variable")
            cred_dict = json.loads(firebase_config_str)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback to file-based config
            cred_path = os.path.join(os.path.dirname(__file__), 'firebase_service_account.json')
            if os.path.exists(cred_path):
                logger.info(f"Loading Firebase service account from file: {cred_path}")
                cred = credentials.Certificate(cred_path)
            else:
                logger.error("Firebase service account file not found")
                raise FileNotFoundError("Firebase service account file not found")
        
        # Initialize Firebase Admin SDK
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    
    # Initialize Firestore
    db = firestore.client()
    logger.info("Firestore client initialized successfully")
    
except FileNotFoundError as e:
    logger.error(f"Firebase service account configuration error: {e}")
    db = None
except ValueError as e:
    logger.error(f"Invalid Firebase service account JSON: {e}")
    db = None
except Exception as e:
    logger.error(f"Error initializing Firebase Admin SDK: {e}")
    db = None

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    # Handle POST request for signup
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        display_name = data.get('displayName')
        age_group = data.get('ageGroup')
        redirect_after_signup = data.get('redirectAfterSignup')
        
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name
        )
        
        # Create user document in Firestore
        user_ref = db.collection('users').document(user.uid)
        user_ref.set({
            'uid': user.uid,
            'email': email,
            'displayName': display_name,
            'ageGroup': age_group,
            'subscription': {
                'plan': 'free',
                'aiAnalysesRemaining': 3,
                'subscriptionDate': datetime.now(),
                'expiryDate': datetime.now() + timedelta(days=30)
            },
            'preferences': {
                'interests': [],
                'location': '',
                'notificationSettings': {
                    'email': True,
                    'push': False
                }
            },
            'createdAt': datetime.now(),
            'updatedAt': datetime.now(),
            'lastLogin': datetime.now()
        })
        
        # Generate custom token for client-side authentication
        custom_token = auth.create_custom_token(user.uid)
        
        response_data = {
            'uid': user.uid,
            'email': email,
            'displayName': display_name,
            'customToken': custom_token.decode('utf-8')
        }
        
        # Include redirectAfterSignup in response if provided
        if redirect_after_signup:
            response_data['redirectAfterSignup'] = redirect_after_signup
        
        return jsonify({
            'success': True,
            'data': response_data
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'SIGNUP_FAILED',
                'message': str(e)
            }
        }), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # Handle POST request for login
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        
        if not id_token:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'ID token is required'
                }
            }), 400
        
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # Get user data from Firestore
        user_ref = db.collection('users').document(uid)
        user_data = user_ref.get()
        
        if not user_data.exists:
            return jsonify({
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found in database'
                }
            }), 404
        
        user_dict = user_data.to_dict()
        
        # Update last login time
        user_ref.update({
            'lastLogin': datetime.now()
        })
        
        # Set session variables
        session['user_id'] = uid
        session['user_email'] = user_dict.get('email')
        session['display_name'] = user_dict.get('displayName')
        
        return jsonify({
            'success': True,
            'data': {
                'uid': uid,
                'email': user_dict.get('email'),
                'displayName': user_dict.get('displayName'),
                'ageGroup': user_dict.get('ageGroup')
            }
        })
        
    except auth.InvalidIdTokenError:
        return jsonify({
            'error': {
                'code': 'INVALID_TOKEN',
                'message': 'Invalid ID token'
            }
        }), 401
    except auth.ExpiredIdTokenError:
        return jsonify({
            'error': {
                'code': 'EXPIRED_TOKEN',
                'message': 'ID token has expired'
            }
        }), 401
    except auth.RevokedIdTokenError:
        return jsonify({
            'error': {
                'code': 'REVOKED_TOKEN',
                'message': 'ID token has been revoked'
            }
        }), 401
    except auth.CertificateFetchError:
        return jsonify({
            'error': {
                'code': 'CERTIFICATE_ERROR',
                'message': 'Error fetching certificate'
            }
        }), 500
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'LOGIN_FAILED',
                'message': str(e)
            }
        }), 400

@app.route('/logout')
def logout():
    # Clear session or handle logout logic
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('profile.html')

@app.route('/api/auth/profile', methods=['GET'])
def api_profile():
    try:
        # Get user ID from session or token
        user_id = request.args.get('uid') or session.get('user_id')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get user data from Firestore
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get()
        
        if not user_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        return jsonify({
            'success': True,
            'data': user_data.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'PROFILE_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

# API endpoint for checking AI analysis limits
@app.route('/api/auth/check-ai-limit', methods=['GET'])
def check_ai_limit():
    try:
        user_id = request.args.get('uid')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'User ID required'
                }
            }), 401
        
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get()
        
        if not user_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'User not found'
                }
            }), 404
        
        user_dict = user_data.to_dict()
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
        return jsonify({
            'error': {
                'code': 'LIMIT_CHECK_FAILED',
                'message': str(e)
            }
        }), 500

# Organization routes
@app.route('/organizations')
def organizations():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('organizations.html')

@app.route('/organizations/create', methods=['GET', 'POST'])
async def organization_create():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('organization_create.html')
    
    # Handle POST request for organization creation
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Comprehensive AI moderation check
        moderation_service = ModerationService(db)
        moderation_result = await moderation_service.moderate_content(data)
        if not moderation_result['approved']:
            return jsonify({
                'error': {
                    'code': 'MODERATION_FAILED',
                    'message': 'Organization content failed moderation check',
                    'details': moderation_result
                }
            }), 400
        
        # Create organization document in Firestore
        org_ref = db.collection('organizations').document()
        organization_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'website': data.get('website', ''),
            'contactEmail': data.get('contactEmail', ''),
            'logo': data.get('logo', ''),
            'category': data.get('category'),
            'tags': normalize_tags(data.get('tags', [])),
            'location': {
                'type': data.get('locationType', 'remote'),
                'address': data.get('address', ''),
                'coordinates': data.get('coordinates', {})
            },
            'openPositions': data.get('openPositions', []),
            'ownerId': user_id,
            'status': 'pending',
            'aiModeration': {
                'status': 'pending',
                'moderationDate': datetime.now(),
                'moderatorNotes': moderation_result.get('notes', '')
            },
            'createdAt': datetime.now(),
            'updatedAt': datetime.now(),
            'viewCount': 0,
            'clickCount': 0
        }
        
        org_ref.set(organization_data)
        
        return jsonify({
            'success': True,
            'data': {
                'id': org_ref.id,
                **organization_data
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'ORG_CREATION_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/organizations/<org_id>')
def organization_view(org_id):
    return render_template('organization_view.html', org_id=org_id)

@app.route('/organizations/<org_id>/edit', methods=['GET', 'POST'])
async def organization_edit(org_id):
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('organization_edit.html', org_id=org_id)
    
    # Handle POST request for organization update
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # Verify user owns the organization
        org_ref = db.collection('organizations').document(org_id)
        org_data = org_ref.get()
        
        if not org_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Organization not found'
                }
            }), 404
        
        org_dict = org_data.to_dict()
        if org_dict.get('ownerId') != user_id:
            return jsonify({
                'error': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'You do not have permission to edit this organization'
                }
            }), 403
        
        # Comprehensive AI moderation check for updates
        moderation_service = ModerationService(db)
        moderation_result = await moderation_service.moderate_content(data)
        if not moderation_result['approved']:
            return jsonify({
                'error': {
                    'code': 'MODERATION_FAILED',
                    'message': 'Organization content failed moderation check',
                    'details': moderation_result
                }
            }), 400
        
        # Update organization document
        update_data = {
            'name': data.get('name', org_dict.get('name')),
            'description': data.get('description', org_dict.get('description')),
            'website': data.get('website', org_dict.get('website', '')),
            'contactEmail': data.get('contactEmail', org_dict.get('contactEmail', '')),
            'logo': data.get('logo', org_dict.get('logo', '')),
            'category': data.get('category', org_dict.get('category')),
            'tags': normalize_tags(data.get('tags', org_dict.get('tags', []))),
            'location': {
                'type': data.get('locationType', org_dict.get('location', {}).get('type', 'remote')),
                'address': data.get('address', org_dict.get('location', {}).get('address', '')),
                'coordinates': data.get('coordinates', org_dict.get('location', {}).get('coordinates', {}))
            },
            'openPositions': data.get('openPositions', org_dict.get('openPositions', [])),
            'updatedAt': datetime.now(),
            'aiModeration.status': 'pending',
            'aiModeration.moderatorNotes': moderation_result.get('notes', '')
        }
        
        org_ref.update(update_data)
        
        return jsonify({
            'success': True,
            'data': {
                'id': org_id,
                **update_data
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'ORG_UPDATE_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/organizations/<org_id>/delete', methods=['POST'])
def organization_delete(org_id):
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({
            'error': {
                'code': 'AUTH_REQUIRED',
                'message': 'Authentication required'
            }
        }), 401
    
    try:
        user_id = session.get('user_id')
        
        # Verify user owns the organization
        org_ref = db.collection('organizations').document(org_id)
        org_data = org_ref.get()
        
        if not org_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Organization not found'
                }
            }), 404
        
        org_dict = org_data.to_dict()
        if org_dict.get('ownerId') != user_id:
            return jsonify({
                'error': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'You do not have permission to delete this organization'
                }
            }), 403
        
        # Delete organization
        org_ref.delete()
        
        return jsonify({
            'success': True,
            'message': 'Organization deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'ORG_DELETION_FAILED',
                'message': str(e)
            }
        }), 500

# API endpoints for organizations
@app.route('/api/organizations', methods=['GET'])
def api_organizations_list():
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        category = request.args.get('category')
        tags = request.args.getlist('tags')
        location_type = request.args.get('location')
        search_query = request.args.get('search')
        
        # Build query
        query = db.collection('organizations').where('status', '==', 'approved')
        
        if category:
            query = query.where('category', '==', category)
        
        if tags:
            query = query.where('tags', 'array_contains_any', tags)
        
        if location_type:
            query = query.where('location.type', '==', location_type)
        
        # Execute query
        organizations = query.limit(limit).offset((page - 1) * limit).get()
        
        org_list = []
        for org in organizations:
            org_data = org.to_dict()
            org_data['id'] = org.id
            
            # Apply search filter if search query is provided
            if search_query:
                search_lower = search_query.lower()
                name_match = search_lower in org_data.get('name', '').lower()
                desc_match = search_lower in org_data.get('description', '').lower()
                tags_match = any(search_lower in tag.lower() for tag in org_data.get('tags', []))
                
                # Only include organization if it matches search criteria
                if name_match or desc_match or tags_match:
                    org_list.append(org_data)
            else:
                org_list.append(org_data)
        
        return jsonify({
            'success': True,
            'data': org_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(org_list)
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'ORG_LIST_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/organizations/<org_id>', methods=['GET'])
def api_organization_get(org_id):
    try:
        org_ref = db.collection('organizations').document(org_id)
        org_data = org_ref.get()
        
        if not org_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Organization not found'
                }
            }), 404
        
        org_dict = org_data.to_dict()
        org_dict['id'] = org_id
        
        return jsonify({
            'success': True,
            'data': org_dict
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'ORG_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/organizations', methods=['POST'])
def api_organization_create():
    return organization_create()

@app.route('/api/organizations/<org_id>', methods=['PUT'])
def api_organization_update(org_id):
    return organization_edit(org_id)

@app.route('/api/organizations/<org_id>', methods=['DELETE'])
def api_organization_delete(org_id):
    return organization_delete(org_id)

# AI suggestion endpoint
@app.route('/api/ai/suggestions', methods=['POST'])
def ai_suggestions():
    try:
        data = request.get_json()
        organization_name = data.get('name', '')
        
        # Placeholder for AI suggestions - will be connected to OpenRouter later
        suggestions = generate_ai_suggestions(organization_name)
        
        return jsonify({
            'success': True,
            'data': suggestions
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'AI_SUGGESTION_FAILED',
                'message': str(e)
            }
        }), 500

# Helper functions
def moderate_organization(data):
    """Basic moderation function for backward compatibility"""
    from moderation_service import moderate_organization as basic_moderate
    return basic_moderate(data)

def generate_ai_suggestions(organization_name):
    """Generate AI suggestions for organization details"""
    # Placeholder implementation - will be connected to OpenRouter
    suggestions = {
        'description': f"A great organization focused on {organization_name}. Join us for amazing opportunities!",
        'tags': ['#stem', '#research', '#innovation'],
        'category': 'remote'
    }
    
    return suggestions

# AI Analysis Routes
@app.route('/ai-analysis')
def ai_analysis():
    """Main AI analysis page"""
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('ai_analysis.html')

@app.route('/api/ai/socratic', methods=['POST'])
async def api_ai_socratic():
    """API endpoint for Socratic questioning"""
    try:
        data = request.get_json()
        user_id = data.get('userId') or session.get('user_id')
        initial_goal = data.get('goal', '')
        
        if not user_id or not initial_goal:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'User ID and goal are required'
                }
            }), 400
        
        # Check AI analysis limits
        limit_check = check_ai_limit(user_id)
        if not limit_check.get('hasAccess', False):
            return jsonify({
                'error': {
                    'code': 'LIMIT_EXCEEDED',
                    'message': 'AI analysis limit exceeded. Upgrade to premium for unlimited analyses.'
                }
            }), 403
        
        # Initialize AI analysis service
        ai_service = AIAnalysisService(db)
        
        # Run Socratic questioning
        result = await ai_service.socratic_questioning(user_id, initial_goal)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Socratic questioning failed: {str(e)}")
        return jsonify({
            'error': {
                'code': 'SOCRATIC_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/ai/debate', methods=['POST'])
async def api_ai_debate():
    """API endpoint for AI debate and consensus building"""
    try:
        data = request.get_json()
        user_id = data.get('userId') or session.get('user_id')
        session_id = data.get('sessionId')
        refined_goal = data.get('refinedGoal', '')
        
        if not user_id or not session_id or not refined_goal:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'User ID, session ID, and refined goal are required'
                }
            }), 400
        
        # Initialize AI analysis service
        ai_service = AIAnalysisService(db)
        
        # Run full AI analysis
        result = await ai_service.full_ai_analysis(user_id, refined_goal)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'error': {
                    'code': 'AI_ANALYSIS_FAILED',
                    'message': result.get('error', 'Unknown error')
                }
            }), 500
            
    except Exception as e:
        logger.error(f"AI debate failed: {str(e)}")
        return jsonify({
            'error': {
                'code': 'DEBATE_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/ai-results/<session_id>')
def ai_results(session_id):
    """Page to display AI analysis results"""
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('ai_results.html', session_id=session_id)

@app.route('/api/ai/results/<session_id>', methods=['GET'])
def api_ai_results(session_id):
    """API endpoint to get AI analysis results"""
    try:
        user_id = request.args.get('uid') or session.get('user_id')
        
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get session data from Firestore
        session_ref = db.collection('ai_sessions').document(session_id)
        session_data = session_ref.get()
        
        if not session_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Session not found'
                }
            }), 404
        
        session_dict = session_data.to_dict()
        
        # Verify user owns this session
        if session_dict.get('userId') != user_id:
            return jsonify({
                'error': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'You do not have permission to view this session'
                }
            }), 403
        
        return jsonify({
            'success': True,
            'data': session_dict
        })
        
    except Exception as e:
        logger.error(f"Error fetching AI results: {str(e)}")
        return jsonify({
            'error': {
                'code': 'RESULTS_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

# Helper function for AI limit checking
def check_ai_limit(user_id):
    """Check if user has AI analysis access"""
    try:
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get()
        
        if not user_data.exists:
            return {'hasAccess': False}
        
        user_dict = user_data.to_dict()
        subscription = user_dict.get('subscription', {})
        plan = subscription.get('plan', 'free')
        remaining = subscription.get('aiAnalysesRemaining', 0)
        
        return {
            'plan': plan,
            'aiAnalysesRemaining': remaining,
            'hasAccess': plan == 'premium' or remaining > 0
        }
        
    except Exception as e:
        logger.error(f"Error checking AI limit: {str(e)}")
        return {'hasAccess': False}

# Test endpoint for AI analysis (development only)
@app.route('/api/ai/test', methods=['GET'])
async def api_ai_test():
    """Test endpoint for AI analysis without OpenRouter API calls"""
    try:
        # Simulate AI responses for testing
        test_responses = {
            "deepseek": "As an admissions officer, I recommend focusing on academic opportunities that align with your long-term goals. Look for programs that offer strong mentorship and networking opportunities.",
            "maverick": "Hey! From a student perspective, I'd say go for something that won't burn you out. Make sure you have time for social life and self-care too!",
            "qwen": "From an HR perspective, consider opportunities that develop transferable skills. Look for roles that offer practical experience and industry connections.",
            "glm": "Reflect on what brings you meaning and fulfillment. Choose paths that align with your values and contribute to personal growth.",
            "grok": "Potential risks: time commitment may be higher than expected, market saturation in some fields, and the possibility of skills becoming outdated quickly."
        }
        
        # Simulate consensus
        test_consensus = {
            "consensus": True,
            "recommendation": "Based on our analysis, we recommend pursuing opportunities that balance academic rigor with practical experience, while ensuring adequate time for personal well-being.",
            "reasoning": "All experts agree on the importance of balanced growth, though they emphasize different aspects (academic, practical, personal)."
        }
        
        return jsonify({
            'success': True,
            'data': {
                'responses': test_responses,
                'consensus': test_consensus,
                'sessionId': 'test-session-123',
                'refinedGoal': 'Test goal for demonstration'
            }
        })
        
    except Exception as e:
        logger.error(f"AI test failed: {str(e)}")
        return jsonify({
            'error': {
                'code': 'TEST_FAILED',
                'message': str(e)
            }
        }), 500

# Dashboard route
@app.route('/dashboard')
def dashboard():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

# API endpoint for user planning data
@app.route('/api/user/planning', methods=['GET'])
def api_user_planning_get():
    try:
        user_id = request.args.get('uid') or session.get('user_id')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get user planning data from Firestore
        planning_ref = db.collection('user_planning').document(user_id)
        planning_data = planning_ref.get()
        
        if not planning_data.exists:
            # Create empty planning document if it doesn't exist
            planning_ref.set({
                'userId': user_id,
                'organizations': [],
                'createdAt': datetime.now(),
                'updatedAt': datetime.now()
            })
            return jsonify({
                'success': True,
                'data': {
                    'userId': user_id,
                    'organizations': []
                }
            })
        
        planning_dict = planning_data.to_dict()
        return jsonify({
            'success': True,
            'data': planning_dict
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'PLANNING_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

# API endpoint to update user planning data
@app.route('/api/user/planning', methods=['POST', 'PUT'])
def api_user_planning_update():
    try:
        user_id = request.args.get('uid') or session.get('user_id')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        data = request.get_json()
        organizations = data.get('organizations', [])
        
        # Update user planning data in Firestore
        planning_ref = db.collection('user_planning').document(user_id)
        planning_ref.set({
            'userId': user_id,
            'organizations': organizations,
            'updatedAt': datetime.now()
        }, merge=True)
        
        return jsonify({
            'success': True,
            'message': 'Planning data updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'PLANNING_UPDATE_FAILED',
                'message': str(e)
            }
        }), 500

# Messaging Routes
@app.route('/messages')
def messages():
    """Main messaging page showing conversations"""
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('messages.html')

@app.route('/messages/<conversation_id>')
def conversation(conversation_id):
    """Individual conversation view"""
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('conversation.html', conversation_id=conversation_id)

@app.route('/api/messages', methods=['GET'])
def api_messages_list():
    """API endpoint to get user's conversations"""
    try:
        user_id = request.args.get('uid') or session.get('user_id')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get conversations where user is either sender or receiver
        conversations_query = db.collection('messages')\
            .where('senderId', '==', user_id)\
            .order_by('createdAt', direction=firestore.DESCENDING)
        
        conversations = conversations_query.get()
        
        # Also get conversations where user is receiver
        received_query = db.collection('messages')\
            .where('receiverId', '==', user_id)\
            .order_by('createdAt', direction=firestore.DESCENDING)
        
        received_conversations = received_query.get()
        
        # Combine and deduplicate conversations
        conversation_map = {}
        
        for conv in conversations:
            conv_data = conv.to_dict()
            conv_data['id'] = conv.id
            other_user_id = conv_data['receiverId']
            conversation_map[other_user_id] = conv_data
        
        for conv in received_conversations:
            conv_data = conv.to_dict()
            conv_data['id'] = conv.id
            other_user_id = conv_data['senderId']
            if other_user_id not in conversation_map:
                conversation_map[other_user_id] = conv_data
        
        # Get user details for each conversation
        conversation_list = []
        for other_user_id, conv_data in conversation_map.items():
            try:
                user_ref = db.collection('users').document(other_user_id)
                user_data = user_ref.get()
                if user_data.exists:
                    user_dict = user_data.to_dict()
                    conversation_list.append({
                        'id': conv_data['id'],
                        'otherUser': {
                            'uid': other_user_id,
                            'displayName': user_dict.get('displayName', 'Unknown User'),
                            'profilePicture': user_dict.get('profilePicture', '')
                        },
                        'lastMessage': conv_data.get('content', ''),
                        'subject': conv_data.get('subject', ''),
                        'timestamp': conv_data.get('createdAt'),
                        'unread': conv_data.get('read', False) == False and conv_data['receiverId'] == user_id
                    })
            except Exception as e:
                logger.error(f"Error fetching user data for {other_user_id}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        conversation_list.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min, reverse=True)
        
        return jsonify({
            'success': True,
            'data': conversation_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return jsonify({
            'error': {
                'code': 'CONVERSATIONS_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/messages/<conversation_id>', methods=['GET'])
def api_messages_get(conversation_id):
    """API endpoint to get messages in a conversation"""
    try:
        user_id = request.args.get('uid') or session.get('user_id')
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get conversation data
        conv_ref = db.collection('messages').document(conversation_id)
        conv_data = conv_ref.get()
        
        if not conv_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Conversation not found'
                }
            }), 404
        
        conv_dict = conv_data.to_dict()
        
        # Verify user is part of this conversation
        if conv_dict['senderId'] != user_id and conv_dict['receiverId'] != user_id:
            return jsonify({
                'error': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'You do not have permission to view this conversation'
                }
            }), 403
        
        # Get all messages in this conversation (between these two users)
        messages_query = db.collection('messages')\
            .where('senderId', 'in', [conv_dict['senderId'], conv_dict['receiverId']])\
            .where('receiverId', 'in', [conv_dict['senderId'], conv_dict['receiverId']])\
            .order_by('createdAt', direction=firestore.DESCENDING)\
            .limit(50)
        
        messages = messages_query.get()
        
        message_list = []
        for msg in messages:
            msg_data = msg.to_dict()
            msg_data['id'] = msg.id
            message_list.append(msg_data)
        
        # Mark messages as read if user is receiver
        if conv_dict['receiverId'] == user_id and not conv_dict.get('read', False):
            conv_ref.update({'read': True, 'updatedAt': datetime.now()})
        
        return jsonify({
            'success': True,
            'data': {
                'conversation': conv_dict,
                'messages': message_list
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({
            'error': {
                'code': 'MESSAGES_FETCH_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/messages', methods=['POST'])
def api_messages_create():
    """API endpoint to send a new message"""
    try:
        data = request.get_json()
        user_id = data.get('senderId') or session.get('user_id')
        receiver_id = data.get('receiverId')
        organization_id = data.get('organizationId')
        content = data.get('content')
        subject = data.get('subject', '')
        
        if not user_id or not receiver_id or not content:
            return jsonify({
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Sender ID, receiver ID, and content are required'
                }
            }), 400
        
        # Create message document in Firestore
        message_ref = db.collection('messages').document()
        message_data = {
            'senderId': user_id,
            'receiverId': receiver_id,
            'organizationId': organization_id,
            'subject': subject,
            'content': content,
            'attachments': data.get('attachments', []),
            'read': False,
            'important': data.get('important', False),
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        }
        
        message_ref.set(message_data)
        
        return jsonify({
            'success': True,
            'data': {
                'id': message_ref.id,
                **message_data
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        return jsonify({
            'error': {
                'code': 'MESSAGE_CREATION_FAILED',
                'message': str(e)
            }
        }), 500

@app.route('/api/messages/<message_id>', methods=['PUT'])
def api_messages_update(message_id):
    """API endpoint to update a message (mark as read/important)"""
    try:
        data = request.get_json()
        user_id = request.args.get('uid') or session.get('user_id')
        
        if not user_id:
            return jsonify({
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required'
                }
            }), 401
        
        # Get message data
        message_ref = db.collection('messages').document(message_id)
        message_data = message_ref.get()
        
        if not message_data.exists:
            return jsonify({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Message not found'
                }
            }), 404
        
        message_dict = message_data.to_dict()
        
        # Verify user is part of this conversation
        if message_dict['senderId'] != user_id and message_dict['receiverId'] != user_id:
            return jsonify({
                'error': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'You do not have permission to update this message'
                }
            }), 403
        
        # Only allow updating read status and important flag
        update_data = {
            'updatedAt': datetime.now()
        }
        
        if 'read' in data and message_dict['receiverId'] == user_id:
            update_data['read'] = data['read']
        
        if 'important' in data:
            update_data['important'] = data['important']
        
        message_ref.update(update_data)
        
        return jsonify({
            'success': True,
            'message': 'Message updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating message: {str(e)}")
        return jsonify({
            'error': {
                'code': 'MESSAGE_UPDATE_FAILED',
                'message': str(e)
            }
        }), 500

# Helper function to get organization owner ID
def get_organization_owner(org_id):
    """Get the owner ID of an organization"""
    try:
        org_ref = db.collection('organizations').document(org_id)
        org_data = org_ref.get()
        
        if org_data.exists:
            org_dict = org_data.to_dict()
            return org_dict.get('ownerId')
        return None
    except Exception as e:
        logger.error(f"Error getting organization owner: {str(e)}")
        return None

# Main index route
@app.route('/')
def index():
    # Inject Algolia credentials into the template
    algolia_app_id = os.environ.get('ALGOLIA_APP_ID', '')
    algolia_api_key = os.environ.get('ALGOLIA_API_KEY', '')
    logger.info(f"Passing Algolia credentials to template - App ID: {'***' if algolia_app_id else 'Not set'}, API Key: {'***' if algolia_api_key else 'Not set'}")
    return render_template('index.html',
                         ALGOLIA_APP_ID=algolia_app_id,
                         ALGOLIA_API_KEY=algolia_api_key)

if __name__ == '__main__':
    app.run(debug=True, port=6000)