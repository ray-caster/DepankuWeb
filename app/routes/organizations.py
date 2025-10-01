# --- app/routes/organizations.py ---
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter

from ..extensions import db 
from ..tasks import moderate_and_index_organization

org_bp = Blueprint('organizations', __name__)
logger = logging.getLogger(__name__)

def normalize_tags(tags):
    """Normalize tags to ensure they start with '#' and are lowercase."""
    if not tags: return []
    normalized = set()
    for tag in tags:
        if isinstance(tag, str):
            clean_tag = tag.strip().lstrip('#').lower()
            if clean_tag:
                normalized.add(f"#{clean_tag}")
    return sorted(list(normalized))

# --- HTML Page Routes ---
# Note: These are kept with the API routes for simplicity in this example.
# In a larger app, they might be in a separate blueprint.

@org_bp.route('/organizations')
def organizations_page():
    initial_query = request.args.get('search', '')
    return render_template('organizations.html', INITIAL_QUERY=initial_query)

@org_bp.route('/organizations/create')
def organization_create_page():
    if 'user_id' not in session: 
        return redirect(url_for('auth.login', redirect=url_for('organizations.organization_create_page')))
    return render_template('organization_create.html')

@org_bp.route('/organizations/<org_id>')
def organization_view_page(org_id):
    return render_template('organization_view.html', org_id=org_id)

@org_bp.route('/organizations/<org_id>/edit')
def organization_edit_page(org_id):
    if 'user_id' not in session: 
        return redirect(url_for('auth.login'))
    return render_template('organization_edit.html', org_id=org_id)


# --- API Endpoints ---
@org_bp.route('/api/organizations', methods=['POST'])
def api_organization_create():
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        org_ref = db.client.collection('organizations').document()
        organization_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'website': data.get('website', ''),
            'contactEmail': data.get('contactEmail', ''),
            'logo': data.get('logo', ''),
            'category': data.get('category'),
            'tags': normalize_tags(data.get('tags', [])),
            'location': data.get('location', {}),
            'openPositions': data.get('openPositions', []),
            'ownerId': user_id,
            'status': 'pending',
            'createdAt': datetime.now(),
            'updatedAt': datetime.now(),
        }
        org_ref.set(organization_data)
        
        moderate_and_index_organization.delay(org_data=organization_data, org_id=org_ref.id)
        
        logger.info(f"Organization {org_ref.id} submitted. Moderation task dispatched.")
        return jsonify({'success': True, 'data': {'id': org_ref.id, **organization_data}}), 202

    except Exception as e:
        logger.error(f"Error creating organization: {e}", exc_info=True)
        return jsonify({'error': 'Failed to create organization.'}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['PUT'])
def api_organization_update(org_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        if not org_doc.exists or org_doc.to_dict().get('ownerId') != user_id:
            return jsonify({'error': 'Permission denied'}), 403

        update_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'website': data.get('website'),
            'contactEmail': data.get('contactEmail'),
            'logo': data.get('logo'),
            'category': data.get('category'),
            'tags': normalize_tags(data.get('tags')),
            'location': data.get('location'),
            'openPositions': data.get('openPositions'),
            'updatedAt': datetime.now(),
            'status': 'pending' # Resubmit for moderation after edits
        }
        # Remove None values so we don't overwrite fields with null
        update_data = {k: v for k, v in update_data.items() if v is not None}

        org_ref.update(update_data)
        
        # Dispatch moderation task again on update
        full_org_data = org_doc.to_dict()
        full_org_data.update(update_data)
        moderate_and_index_organization.delay(org_data=full_org_data, org_id=org_id)

        logger.info(f"Organization {org_id} updated. Moderation task re-dispatched.")
        return jsonify({'success': True, 'data': {'id': org_id, **update_data}}), 202
    except Exception as e:
        logger.error(f"Error updating organization {org_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update organization.'}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['DELETE'])
def api_organization_delete(org_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        user_id = session['user_id']
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        
        if not org_doc.exists:
            return jsonify({'error': 'Organization not found'}), 404
        if org_doc.to_dict().get('ownerId') != user_id:
            return jsonify({'error': 'Permission denied'}), 403
            
        org_ref.delete()
        
        # Future integration: Remove from search index
        # from app.services.search_service import algolia_client
        # algolia_client.delete_organization(org_id)
        
        logger.info(f"Organization {org_id} deleted by user {user_id}.")
        return jsonify({'success': True, 'message': 'Organization deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting organization {org_id}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete organization.'}), 500

@org_bp.route('/api/organizations/<org_id>', methods=['GET'])
def api_organization_get(org_id):
    try:
        org_ref = db.client.collection('organizations').document(org_id)
        org_doc = org_ref.get()
        if not org_doc.exists:
            return jsonify({'error': 'Organization not found'}), 404
        
        org_data = org_doc.to_dict()
        # Ensure ownerId is not sent to unauthorized users
        is_owner = session.get('user_id') == org_data.get('ownerId')
        if not is_owner:
            org_data.pop('ownerId', None)
            org_data.pop('aiModeration', None)

        return jsonify({'success': True, 'data': {'id': org_id, **org_data}})
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve organization.'}), 500

@org_bp.route('/api/organizations', methods=['GET'])
def api_organizations_list():
    try:
        limit = int(request.args.get('limit', 20))
        # This is a simple list for non-search purposes, filtering by approved status
        query = db.client.collection('organizations').where(
            filter=FieldFilter('status', '==', 'approved')
        ).limit(limit)
        
        docs = query.stream()
        org_list = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return jsonify({'success': True, 'data': org_list})
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve organizations.'}), 500