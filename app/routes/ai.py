import asyncio
from flask import Blueprint, request, jsonify, session, render_template, url_for, redirect
import logging

from ..extensions import db
from ..services.ai_analysis_service import AIAnalysisService

ai_bp = Blueprint('ai', __name__)
logger = logging.getLogger(__name__)

# --- HTML Page Routes ---
@ai_bp.route('/analysis')
def ai_analysis_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('ai_analysis.html')

@ai_bp.route('/results/<session_id>')
def ai_results_page(session_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('ai_results.html', session_id=session_id)

# --- API Endpoints ---
@ai_bp.route('/socratic', methods=['POST'])
def api_ai_socratic():
    if 'user_id' not in session:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    try:
        data = request.get_json()
        user_id = session['user_id']
        initial_goal = data.get('goal')
        if not initial_goal:
            return jsonify({'error': {'code': 'INVALID_REQUEST', 'message': 'Goal is required'}}), 400
        
        ai_service = AIAnalysisService(db.client)
        # Run the async function from a sync context
        result = asyncio.run(ai_service.socratic_questioning(user_id, initial_goal))
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Socratic API failed: {e}")
        return jsonify({'error': {'code': 'SOCRATIC_FAILED', 'message': 'Socratic questioning process failed.'}}), 500

@ai_bp.route('/debate', methods=['POST'])
def api_ai_debate():
    if 'user_id' not in session:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401

    try:
        data = request.get_json()
        user_id = session['user_id']
        session_id = data.get('sessionId')
        refined_goal = data.get('refinedGoal')
        if not all([session_id, refined_goal]):
            return jsonify({'error': {'code': 'INVALID_REQUEST', 'message': 'Session ID and refined goal are required'}}), 400

        ai_service = AIAnalysisService(db.client)
        # Run the async function from a sync context
        result = asyncio.run(ai_service.full_ai_analysis_flow(user_id, refined_goal))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Debate API failed: {e}")
        return jsonify({'error': {'code': 'DEBATE_FAILED', 'message': 'AI debate process failed.'}}), 500

# FIXED: Route conflict. Changed URL to /api/results/...
@ai_bp.route('/api/results/<session_id>', methods=['GET'])
def get_ai_results_api(session_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    try:
        session_ref = db.client.collection('ai_sessions').document(session_id)
        session_doc = session_ref.get()
        if not session_doc.exists:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Session not found'}}), 404
        
        session_dict = session_doc.to_dict()
        if session_dict.get('userId') != user_id:
            return jsonify({'error': {'code': 'PERMISSION_DENIED', 'message': 'You do not have permission to view this session'}}), 403
            
        return jsonify({'success': True, 'data': session_dict})
    except Exception as e:
        logger.error(f"Failed to fetch AI results for session {session_id}: {e}")
        return jsonify({'error': {'code': 'RESULTS_FETCH_FAILED', 'message': 'Could not retrieve results.'}}), 500