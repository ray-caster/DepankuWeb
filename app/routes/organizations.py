import os
import asyncio
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from datetime import datetime
import logging

from ..extensions import db 
from ..services.moderation_service import ModerationService

org_bp = Blueprint('organizations', __name__)
logger = logging.getLogger(__name__)

def normalize_tags(tags):
    """Normalize tags to ensure they start with '#' and are lowercase."""
    if not tags: return []
    normalized = []
    for tag in tags:
        if isinstance(tag, str):
            tag = tag.strip().lstrip('#')
            if tag: normalized.append(f"#{tag.lower()}")
    return list(set(normalized)) # Remove duplicates

# --- HTML Page Routes ---
@org_bp.route('/organizations')
def organizations_page():
    algolia_app_id = os.environ.get('ALGOLIA_APP_ID', '')
    algolia_search_key = os.environ.get('ALGOLIA_SEARCH_KEY', '') 
    initial_query = request.args.get('search', '')
    return render_template('organizations.html',
                           ALGOLIA_APP_ID=algolia_app_id,
                           ALGOLIA_API_KEY=algolia_search_key,
                           INITIAL_QUERY=initial_query)

@org_bp.route('/organizations/create')
def organization_create_page():
    if 'user_id' not in session: return redirect(url_for('main.index'))
    return render_template('organization_create.html')

@org_bp.route('/organizations/<org_id>')
def organization_view(org_id):
    return render_template('organization_view.html', org_id=org_id)

@org_bp.route('/organizations/<org_id>/edit')
def organization_edit_page(org_id):
    if 'user_id' not in session: return redirect(url_for('main.index'))
    return render_template('organization_edit.html', org_id=org_id)

# --- API Endpoints ---
@org_bp.route('/api/organizations', methods=['POST'])
def api_organization_create():
    if 'user_id' not in session:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        moderation_service = ModerationService(db.client)
        moderation_result = asyncio.run(moderation_service.moderate_content(data))
        if not moderation_result.get('approved', True):
            return jsonify({'error': {'code': 'MODERATION_FAILED', 'message': 'Content failed moderation', 'details': moderation_result}}), 400
        
        org_ref = db.client.collection('organizations').document()
        organization_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'website': data.get('website', ''),
            'contactEmail': data.get('contactEmail', ''),
            'logo': data.get('logo', ''),
            'category': data.get('category'),
            'tags': normalize_tags(data.get('tags', [])),
            'location': {'type': data.get('locationType', 'remote'), 'address': data.get('address', '')},
            'openPositions': data.get('openPositions', []),
            'ownerId': user_id,
            'status': 'pending',
            'aiModeration': moderation_result,
            'createdAt': datetime.now(),
            'updatedAt': datetime.now(),
            'viewCount': 0, 'clickCount': 0
        }
        org_ref.set(organization_data)
        
        logger.info(f"Organization {org_ref.id} created by {user_id}. Needs to be indexed in Algolia.")
        return jsonify({'success': True, 'data': {'id': org_ref.id, **organization_data}}), 201
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        return jsonify({'error': {'code': 'ORG_CREATION_FAILED', 'message': 'Failed to create organization.'}}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['PUT'])
def api_organization_update(org_id):
    if 'user_id' not in session:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        if not org_doc.exists or org_doc.to_dict().get('ownerId') != user_id:
            return jsonify({'error': {'code': 'PERMISSION_DENIED', 'message': 'Organization not found or permission denied'}}), 403

        moderation_service = ModerationService(db.client)
        moderation_result = asyncio.run(moderation_service.moderate_content(data))
        if not moderation_result.get('approved', True):
            return jsonify({'error': {'code': 'MODERATION_FAILED', 'message': 'Updated content failed moderation', 'details': moderation_result}}), 400

        update_data = {key: value for key, value in {
            'name': data.get('name'),
            'description': data.get('description'),
            'website': data.get('website'),
            'contactEmail': data.get('contactEmail'),
            'logo': data.get('logo'),
            'category': data.get('category'),
            'tags': normalize_tags(data.get('tags')),
            'location': data.get('location'),
            'openPositions': data.get('openPositions')
        }.items() if value is not None}
        
        update_data['updatedAt'] = datetime.now()
        update_data['aiModeration'] = moderation_result
        update_data['status'] = 'pending'

        org_ref.update(update_data)
        logger.info(f"Organization {org_id} updated by {user_id}. Needs to be re-indexed in Algolia.")
        return jsonify({'success': True, 'data': {'id': org_id, **update_data}})
    except Exception as e:
        logger.error(f"Error updating organization {org_id}: {e}")
        return jsonify({'error': {'code': 'ORG_UPDATE_FAILED', 'message': 'Failed to update organization.'}}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['DELETE'])
def api_organization_delete(org_id):
    if 'user_id' not in session:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    try:
        user_id = session['user_id']
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Organization not found'}}), 404
            
        if org_doc.to_dict().get('ownerId') != user_id:
            return jsonify({'error': {'code': 'PERMISSION_DENIED', 'message': 'You do not have permission to delete this organization'}}), 403
            
        org_ref.delete()
        
        logger.info(f"Organization {org_id} deleted by {user_id}. Needs to be removed from Algolia index.")
        return jsonify({'success': True, 'message': 'Organization deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting organization {org_id}: {e}")
        return jsonify({'error': {'code': 'ORG_DELETION_FAILED', 'message': 'Failed to delete organization.'}}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['GET'])
def api_organization_get(org_id):
    try:
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Organization not found'}}), 404
        return jsonify({'success': True, 'data': {'id': org_id, **org_doc.to_dict()}})
    except Exception as e:
        return jsonify({'error': {'code': 'ORG_FETCH_FAILED', 'message': 'Failed to retrieve organization.'}}), 500

@org_bp.route('/api/organizations', methods=['GET'])
def api_organizations_list():
    try:
        limit = int(request.args.get('limit', 20))
        query = db.client.collection('organizations').where(filter=FieldFilter('status', '==', 'approved')).limit(limit)
        docs = query.stream()
        org_list = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return jsonify({'success': True, 'data': org_list})
    except Exception as e:
        return jsonify({'error': {'code': 'ORG_LIST_FAILED', 'message': 'Failed to retrieve organizations.'}}), 500