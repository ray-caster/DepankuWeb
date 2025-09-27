// Depanku Messaging Client-Side JavaScript
class MessagingSystem {
    constructor() {
        this.currentUser = null;
        this.currentConversation = null;
        this.conversations = [];
        this.messages = [];
        this.firestore = null;
        this.unsubscribeListeners = [];
        
        this.initializeFirebase();
        this.bindEvents();
    }

    // Initialize Firebase client SDK
    initializeFirebase() {
        // This would typically be initialized from firebase_config.json
        // For now, we'll use direct API calls to Flask backend
        console.log("Messaging system initialized");
    }

    // Bind event listeners
    bindEvents() {
        // Messages page events
        if (document.getElementById('newConversationBtn')) {
            document.getElementById('newConversationBtn').addEventListener('click', () => {
                this.showNewConversationModal();
            });
        }

        if (document.getElementById('searchInput')) {
            document.getElementById('searchInput').addEventListener('input', (e) => {
                this.filterConversations(e.target.value);
            });
        }

        // Conversation page events
        if (document.getElementById('messageForm')) {
            document.getElementById('messageForm').addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // New conversation modal events
        if (document.getElementById('newConversationForm')) {
            document.getElementById('newConversationForm').addEventListener('submit', (e) => {
                e.preventDefault();
                this.createNewConversation();
            });
        }
    }

    // Load user's conversations
    async loadConversations() {
        try {
            const response = await axios.get('/api/messages');
            if (response.data.success) {
                this.conversations = response.data.data;
                this.renderConversations();
            } else {
                console.error('Failed to load conversations:', response.data.error);
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showError('Failed to load conversations');
        }
    }

    // Render conversations list
    renderConversations() {
        const container = document.getElementById('conversationsList');
        const emptyState = document.getElementById('emptyState');
        
        if (!container) return;

        if (this.conversations.length === 0) {
            container.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        container.style.display = 'block';

        container.innerHTML = this.conversations.map(conv => `
            <div class="conversation-item" data-conversation-id="${conv.id}" data-user-id="${conv.otherUser.uid}">
                <div class="d-flex align-items-center">
                    <img src="${conv.otherUser.profilePicture || '/static/images/default-avatar.png'}" 
                         alt="${conv.otherUser.displayName}" 
                         class="conversation-avatar"
                         onerror="this.src='/static/images/default-avatar.png'">
                    <div class="conversation-content">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="conversation-name">${conv.otherUser.displayName}</h6>
                            <span class="conversation-time">${this.formatTime(conv.timestamp)}</span>
                        </div>
                        <p class="conversation-preview">${this.truncateText(conv.lastMessage, 50)}</p>
                    </div>
                    ${conv.unread ? '<span class="conversation-badge">!</span>' : ''}
                </div>
            </div>
        `).join('');

        // Add click listeners to conversation items
        container.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const conversationId = item.getAttribute('data-conversation-id');
                const userId = item.getAttribute('data-user-id');
                window.location.href = `/messages/${conversationId}`;
            });
        });
    }

    // Filter conversations based on search input
    filterConversations(searchTerm) {
        const filtered = this.conversations.filter(conv =>
            conv.otherUser.displayName.toLowerCase().includes(searchTerm.toLowerCase()) ||
            conv.lastMessage.toLowerCase().includes(searchTerm.toLowerCase()) ||
            conv.subject.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderFilteredConversations(filtered);
    }

    // Render filtered conversations
    renderFilteredConversations(conversations) {
        const container = document.getElementById('conversationsList');
        if (!container) return;

        container.innerHTML = conversations.map(conv => `
            <div class="conversation-item" data-conversation-id="${conv.id}" data-user-id="${conv.otherUser.uid}">
                <div class="d-flex align-items-center">
                    <img src="${conv.otherUser.profilePicture || '/static/images/default-avatar.png'}" 
                         alt="${conv.otherUser.displayName}" 
                         class="conversation-avatar"
                         onerror="this.src='/static/images/default-avatar.png'">
                    <div class="conversation-content">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="conversation-name">${conv.otherUser.displayName}</h6>
                            <span class="conversation-time">${this.formatTime(conv.timestamp)}</span>
                        </div>
                        <p class="conversation-preview">${this.truncateText(conv.lastMessage, 50)}</p>
                    </div>
                    ${conv.unread ? '<span class="conversation-badge">!</span>' : ''}
                </div>
            </div>
        `).join('');

        // Add click listeners
        container.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const conversationId = item.getAttribute('data-conversation-id');
                window.location.href = `/messages/${conversationId}`;
            });
        });
    }

    // Load specific conversation messages
    async loadConversation(conversationId) {
        try {
            const response = await axios.get(`/api/messages/${conversationId}`);
            if (response.data.success) {
                this.currentConversation = response.data.data.conversation;
                this.messages = response.data.data.messages;
                this.renderConversationHeader();
                this.renderMessages();
                this.setupRealTimeListener();
            } else {
                console.error('Failed to load conversation:', response.data.error);
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Failed to load conversation');
        }
    }

    // Render conversation header with user info
    renderConversationHeader() {
        if (!this.currentConversation) return;

        const otherUserId = this.currentConversation.senderId === this.getCurrentUserId() ? 
            this.currentConversation.receiverId : this.currentConversation.senderId;

        document.getElementById('conversationTitle').textContent = 'Conversation';
        document.getElementById('conversationSubject').textContent = `Subject: ${this.currentConversation.subject || 'No subject'}`;

        // Fetch user details for the header
        this.fetchUserDetails(otherUserId).then(user => {
            if (user) {
                document.getElementById('otherUserName').textContent = user.displayName;
                const avatar = document.getElementById('otherUserAvatar');
                if (avatar && user.profilePicture) {
                    avatar.src = user.profilePicture;
                    avatar.style.display = 'block';
                }
            }
        });
    }

    // Render messages in the conversation
    renderMessages() {
        const container = document.getElementById('messagesContainer');
        if (!container) return;

        container.innerHTML = this.messages.map(msg => `
            <div class="message ${msg.senderId === this.getCurrentUserId() ? 'sent' : 'received'}">
                <div class="message-bubble">
                    <p class="mb-1">${this.escapeHtml(msg.content)}</p>
                    <div class="message-time">
                        ${this.formatTime(msg.createdAt)}
                    </div>
                </div>
            </div>
        `).join('');

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    // Send a new message
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();
        
        if (!content) return;

        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;

        try {
            const messageData = {
                receiverId: this.currentConversation.senderId === this.getCurrentUserId() ? 
                    this.currentConversation.receiverId : this.currentConversation.senderId,
                content: content,
                subject: this.currentConversation.subject,
                organizationId: this.currentConversation.organizationId
            };

            const response = await axios.post('/api/messages', messageData);
            
            if (response.data.success) {
                messageInput.value = '';
                this.messages.unshift(response.data.data);
                this.renderMessages();
            } else {
                this.showError('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message');
        } finally {
            sendBtn.disabled = false;
        }
    }

    // Show new conversation modal
    async showNewConversationModal() {
        const modal = new bootstrap.Modal(document.getElementById('newConversationModal'));
        await this.loadOrganizationOwners();
        modal.show();
    }

    // Load organization owners for new conversation
    async loadOrganizationOwners() {
        try {
            const response = await axios.get('/api/organizations?limit=100');
            const select = document.getElementById('receiverSelect');
            
            if (response.data.success) {
                // Clear existing options except the first one
                while (select.options.length > 1) {
                    select.remove(1);
                }

                // Add organization owners
                response.data.data.forEach(org => {
                    const option = document.createElement('option');
                    option.value = org.ownerId;
                    option.textContent = `${org.name} (Owner: ${org.ownerId})`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading organization owners:', error);
        }
    }

    // Create new conversation
    async createNewConversation() {
        const receiverSelect = document.getElementById('receiverSelect');
        const subjectInput = document.getElementById('subjectInput');
        const messageContent = document.getElementById('messageContent');

        const receiverId = receiverSelect.value;
        const subject = subjectInput.value.trim();
        const content = messageContent.value.trim();

        if (!receiverId || !subject || !content) {
            this.showError('Please fill all fields');
            return;
        }

        try {
            const messageData = {
                receiverId: receiverId,
                subject: subject,
                content: content
            };

            const response = await axios.post('/api/messages', messageData);
            
            if (response.data.success) {
                // Close modal and redirect to new conversation
                const modal = bootstrap.Modal.getInstance(document.getElementById('newConversationModal'));
                modal.hide();
                window.location.href = `/messages/${response.data.data.id}`;
            } else {
                this.showError('Failed to create conversation');
            }
        } catch (error) {
            console.error('Error creating conversation:', error);
            this.showError('Failed to create conversation');
        }
    }

    // Setup real-time listener for new messages
    setupRealTimeListener() {
        // This would use Firebase Firestore real-time listeners
        // For now, we'll use polling or WebSocket implementation
        console.log("Real-time messaging would be implemented here with Firebase");
    }

    // Helper methods
    getCurrentUserId() {
        // This should get the current user ID from session or Firebase auth
        // For now, we'll use a placeholder
        return 'current-user-id-placeholder';
    }

    async fetchUserDetails(userId) {
        try {
            const response = await axios.get(`/api/auth/profile?uid=${userId}`);
            if (response.data.success) {
                return response.data.data;
            }
        } catch (error) {
            console.error('Error fetching user details:', error);
        }
        return null;
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        
        const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    truncateText(text, length) {
        return text.length > length ? text.substring(0, length) + '...' : text;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        alert(message);
    }

    showSuccess(message) {
        // Simple success display
        alert(message);
    }
}

// Initialize messaging system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.messagingSystem = new MessagingSystem();
    
    // Load conversations if on messages page
    if (window.location.pathname === '/messages') {
        window.messagingSystem.loadConversations();
    }
    
    // Load specific conversation if on conversation page
    const conversationMatch = window.location.pathname.match(/\/messages\/([^\/]+)/);
    if (conversationMatch) {
        window.messagingSystem.loadConversation(conversationMatch[1]);
    }
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MessagingSystem;
}