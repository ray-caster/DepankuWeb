from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from datetime import datetime
import logging

from ..extensions import db

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)

# --- HTML Page Routes ---
@dashboard_bp.route('/')
def dashboard_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')

# --- API Endpoints ---
@dashboard_bp.route('/api/planning', methods=['GET', 'POST'])
def handle_planning_board():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    planning_ref = db.client.collection('user_planning').document(user_id)
    
    if request.method == 'GET':
        try:
            planning_doc = planning_ref.get()
            if not planning_doc.exists:
                # Create a default planning doc if it doesn't exist
                default_data = {'userId': user_id, 'organizations': [], 'createdAt': datetime.now(), 'updatedAt': datetime.now()}
                planning_ref.set(default_data)
                return jsonify({'success': True, 'data': default_data})
            return jsonify({'success': True, 'data': planning_doc.to_dict()})
        except Exception as e:
            return jsonify({'error': {'code': 'PLANNING_FETCH_FAILED', 'message': str(e)}}), 500
            
    if request.method == 'POST':
        try:
            data = request.get_json()
            organizations = data.get('organizations', [])
            planning_ref.set({
                'userId': user_id,
                'organizations': organizations,
                'updatedAt': datetime.now()
            }, merge=True)
            return jsonify({'success': True, 'message': 'Planning board updated successfully'})
        except Exception as e:
            return jsonify({'error': {'code': 'PLANNING_UPDATE_FAILED', 'message': str(e)}}), 500