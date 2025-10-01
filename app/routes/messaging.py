from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from datetime import datetime
import logging
from google.cloud.firestore_v1.base_query import FieldFilter

from ..extensions import db

messaging_bp = Blueprint('messaging', __name__)
logger = logging.getLogger(__name__)

# --- HTML Page Routes ---
@messaging_bp.route('/')
def messages_page():
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    return render_template('messages.html')

@messaging_bp.route('/<conversation_id>')
def conversation_page(conversation_id):
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    # FIX: Pass the conversation_id to the template
    return render_template('conversation.html', conversation_id=conversation_id)

# --- API Endpoints ---
@messaging_bp.route('/api/conversations', methods=['GET'])
def get_conversations():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    try:
        # Query for messages where the user is the sender OR receiver
        sent_query = db.client.collection('messages').where(filter=FieldFilter('senderId', '==', user_id)).stream()
        received_query = db.client.collection('messages').where(filter=FieldFilter('receiverId', '==', user_id)).stream()

        # Use a dictionary to store the latest message for each conversation partner
        conversations = {}
        
        for msg_doc in sent_query:
            msg = msg_doc.to_dict()
            partner_id = msg['receiverId']
            if partner_id not in conversations or msg['createdAt'] > conversations[partner_id]['createdAt']:
                conversations[partner_id] = msg
                conversations[partner_id]['id'] = msg_doc.id

        for msg_doc in received_query:
            msg = msg_doc.to_dict()
            partner_id = msg['senderId']
            if partner_id not in conversations or msg['createdAt'] > conversations[partner_id]['createdAt']:
                conversations[partner_id] = msg
                conversations[partner_id]['id'] = msg_doc.id

        # Fetch user details for each conversation partner
        user_ids = list(conversations.keys())
        users_info = {}
        if user_ids:
            # Firestore 'in' query can take a list of up to 30 elements
            user_docs = db.client.collection('users').where(filter=FieldFilter('uid', 'in', user_ids)).stream()
            for user_doc in user_docs:
                user_data = user_doc.to_dict()
                users_info[user_doc.id] = {
                    'displayName': user_data.get('displayName', 'Unknown User'),
                    'profilePicture': user_data.get('profilePicture', '')
                }

        # Format the response
        response_data = []
        for partner_id, msg in conversations.items():
            response_data.append({
                'id': msg.get('id', partner_id), # Use partner_id as a fallback conversation identifier
                'lastMessage': msg.get('content', ''),
                'timestamp': msg.get('createdAt'),
                'subject': msg.get('subject', ''),
                'unread': not msg.get('read', False) and msg.get('receiverId') == user_id,
                'otherUser': {
                    'uid': partner_id,
                    **users_info.get(partner_id, {'displayName': 'Unknown User', 'profilePicture': ''})
                }
            })

        # Sort by most recent message
        response_data.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({'success': True, 'data': response_data})
    except Exception as e:
        logger.error(f"Error fetching conversations for user {user_id}: {e}")
        return jsonify({'error': {'code': 'CONVERSATIONS_FETCH_FAILED', 'message': 'Failed to retrieve conversations.'}}), 500


@messaging_bp.route('/api/thread/<other_user_id>', methods=['GET'])
def get_message_thread(other_user_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401
    
    try:
        participants = [user_id, other_user_id]
        
        # Perform two queries and merge client-side
        q1 = db.client.collection('messages').where(filter=FieldFilter('senderId', '==', user_id)).where(filter=FieldFilter('receiverId', '==', other_user_id)).stream()
        q2 = db.client.collection('messages').where(filter=FieldFilter('senderId', '==', other_user_id)).where(filter=FieldFilter('receiverId', '==', user_id)).stream()
        
        messages = []
        for doc in q1:
            messages.append({'id': doc.id, **doc.to_dict()})
        for doc in q2:
            messages.append({'id': doc.id, **doc.to_dict()})
        
        # Sort messages chronologically
        messages.sort(key=lambda x: x['createdAt'])

        # Mark messages as read
        unread_batch = db.client.batch()
        marked_as_read = False
        for msg in messages:
            if msg.get('receiverId') == user_id and not msg.get('read'):
                msg_ref = db.client.collection('messages').document(msg['id'])
                unread_batch.update(msg_ref, {'read': True, 'updatedAt': datetime.now()})
                marked_as_read = True
        
        if marked_as_read:
            unread_batch.commit()

        return jsonify({'success': True, 'data': messages})
    except Exception as e:
        logger.error(f"Error fetching thread between {user_id} and {other_user_id}: {e}")
        return jsonify({'error': {'code': 'MESSAGES_FETCH_FAILED', 'message': 'Failed to retrieve message thread.'}}), 500


@messaging_bp.route('/api/send', methods=['POST'])
def send_message():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': {'code': 'AUTH_REQUIRED', 'message': 'Authentication required'}}), 401

    try:
        data = request.get_json()
        receiver_id = data.get('receiverId')
        content = data.get('content')
        if not receiver_id or not content:
            return jsonify({'error': {'code': 'INVALID_REQUEST', 'message': 'Receiver and content are required'}}), 400

        msg_ref = db.client.collection('messages').document()
        message_data = {
            'senderId': user_id,
            'receiverId': receiver_id,
            'organizationId': data.get('organizationId'),
            'subject': data.get('subject', 'No Subject'),
            'content': content,
            'attachments': data.get('attachments', []),
            'read': False,
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        }
        msg_ref.set(message_data)

        return jsonify({'success': True, 'data': {'id': msg_ref.id, **message_data}}), 201
    except Exception as e:
        logger.error(f"Error sending message from {user_id}: {e}")
        return jsonify({'error': {'code': 'MESSAGE_SEND_FAILED', 'message': 'Failed to send message.'}}), 500