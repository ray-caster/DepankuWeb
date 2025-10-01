# --- app/routes/ai.py ---
import logging
from flask import Blueprint, request, jsonify, session, render_template, url_for, redirect
from celery.result import AsyncResult

from ..extensions import db, celery
from ..tasks import perform_ai_analysis
from ..services.ai_analysis_service import AIAnalysisService
from ..services.openai_service import OpenAIService

ai_bp = Blueprint('ai', __name__)
logger = logging.getLogger(__name__)

# --- HTML Page Routes (Unchanged) ---
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

@ai_bp.route('/api/socratic/start', methods=['POST'])
def api_socratic_start():
    """Starts a new Socratic questioning session."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        user_id = session['user_id']
        initial_goal = data.get('goal')
        if not initial_goal:
            return jsonify({'error': 'Initial goal is required'}), 400

        ai_service = AIAnalysisService(db.client, OpenAIService())
        result = ai_service.start_socratic_session(user_id, initial_goal)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Socratic start API failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to start Socratic questioning process.'}), 500

@ai_bp.route('/api/socratic/respond', methods=['POST'])
def api_socratic_respond():
    """Continues a Socratic questioning session with a user's answer."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        session_id = data.get('sessionId')
        answer = data.get('answer')
        if not all([session_id, answer]):
            return jsonify({'error': 'Session ID and answer are required'}), 400

        ai_service = AIAnalysisService(db.client, OpenAIService())
        result = ai_service.continue_socratic_session(session_id, answer)

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Socratic respond API failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process your response.'}), 500

@ai_bp.route('/debate', methods=['POST'])
def api_ai_debate():
    """Starts the full AI debate as a background task."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    user_id = session['user_id']
    session_id = data.get('sessionId')
    refined_goal = data.get('refinedGoal')
    if not all([session_id, refined_goal]):
        return jsonify({'error': 'Session ID and refined goal are required'}), 400

    try:
        # Dispatch the long-running analysis to a Celery worker
        task = perform_ai_analysis.delay(user_id, refined_goal, session_id)
        
        # Immediately respond with the task ID
        return jsonify({
            'success': True,
            'message': 'AI analysis has been started.',
            'task_id': task.id
        }), 202  # 202 Accepted
    except Exception as e:
        logger.error(f"Failed to start AI analysis task: {e}", exc_info=True)
        return jsonify({'error': 'Failed to start the AI analysis process.'}), 500

@ai_bp.route('/api/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Polls for the status and result of a Celery task."""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    task_result = AsyncResult(task_id, app=celery)
    
    response = {
        'task_id': task_id,
        'state': task_result.state,
        'info': task_result.info,
    }
    
    if task_result.successful():
        response['result'] = task_result.get()
    elif task_result.failed():
        response['error'] = 'Task failed to complete.'
        logger.error(f"Task {task_id} failed with info: {task_result.info}")

    return jsonify(response)

@ai_bp.route('/api/results/<session_id>', methods=['GET'])
def get_ai_results_api(session_id):
    """Fetches the final AI session results from Firestore."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        session_ref = db.client.collection('ai_sessions').document(session_id)
        session_doc = session_ref.get()
        if not session_doc.exists:
            return jsonify({'error': 'Session not found'}), 404
        
        session_dict = session_doc.to_dict()
        if session_dict.get('userId') != user_id:
            return jsonify({'error': 'Permission denied'}), 403
            
        return jsonify({'success': True, 'data': session_dict})
    except Exception as e:
        logger.error(f"Failed to fetch AI results for session {session_id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not retrieve results.'}), 500