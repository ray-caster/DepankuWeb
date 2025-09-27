// Organizations JavaScript - Client-side functionality for organization management

class OrganizationsManager {
    constructor() {
        this.currentOrgId = null;
        this.init();
    }

    init() {
        // Initialize based on current page
        const path = window.location.pathname;
        
        if (path === '/organizations') {
            this.loadUserOrganizations();
        } else if (path === '/organizations/create') {
            this.initCreateForm();
        } else if (path.startsWith('/organizations/') && path.endsWith('/edit')) {
            this.initEditForm();
        }
    }

    // Load user's organizations
    async loadUserOrganizations() {
        try {
            // This would typically use Firebase Auth to get current user
            // For now, we'll use a placeholder - in real implementation, use Firebase Auth
            const user = this.getCurrentUser();
            
            if (!user) {
                window.location.href = '/login';
                return;
            }

            // Build query to get user's organizations
            // Note: This would need proper Firestore querying in a real implementation
            const response = await axios.get('/api/organizations', {
                params: {
                    owner: user.uid // This would need backend support for filtering by owner
                }
            });

            const organizations = response.data.data;
            this.renderOrganizations(organizations);

        } catch (error) {
            console.error('Error loading organizations:', error);
            this.showError('Failed to load organizations. Please try again.');
        }
    }

    // Render organizations list
    renderOrganizations(organizations) {
        const container = document.getElementById('organizations-list');
        const noOrgs = document.getElementById('no-organizations');

        if (!organizations || organizations.length === 0) {
            container.style.display = 'none';
            noOrgs.classList.remove('d-none');
            return;
        }

        container.innerHTML = '';
        noOrgs.classList.add('d-none');

        organizations.forEach(org => {
            const orgCard = this.createOrganizationCard(org);
            container.appendChild(orgCard);
        });
    }

    // Create organization card HTML
    createOrganizationCard(org) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-4';

        col.innerHTML = `
            <div class="card h-100">
                ${org.logo ? `
                    <img src="${org.logo}" class="card-img-top" alt="${org.name}" style="height: 160px; object-fit: cover;">
                ` : `
                    <div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height: 160px;">
                        <i class="fas fa-building fa-3x text-muted"></i>
                    </div>
                `}
                <div class="card-body">
                    <h5 class="card-title">${org.name}</h5>
                    <div class="d-flex flex-wrap mb-2">
                        <span class="badge bg-primary me-1 mb-1">${org.category}</span>
                        <span class="badge bg-secondary me-1 mb-1">${org.location?.type}</span>
                    </div>
                    <p class="card-text text-muted small">${org.description?.substring(0, 100)}${org.description?.length > 100 ? '...' : ''}</p>
                    <div class="d-flex flex-wrap">
                        ${org.tags?.slice(0, 3).map(tag => `
                            <span class="badge bg-light text-dark me-1 mb-1">${tag}</span>
                        `).join('')}
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <div class="d-flex justify-content-between">
                        <a href="/organizations/${org.id}" class="btn btn-sm btn-outline-primary">
                            View Details
                        </a>
                        <div class="btn-group">
                            <a href="/organizations/${org.id}/edit" class="btn btn-sm btn-outline-secondary">
                                <i class="fas fa-edit"></i>
                            </a>
                            <button class="btn btn-sm btn-outline-danger" onclick="organizationsManager.deleteOrganization('${org.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        return col;
    }

    // Initialize create form
    initCreateForm() {
        const form = document.getElementById('organizationForm');
        const addPositionBtn = document.getElementById('addPosition');
        const aiSuggestBtn = document.getElementById('aiSuggestBasic');

        // Add first position by default
        this.addPosition();

        // Handle form submission
        form.addEventListener('submit', (e) => this.handleCreateSubmit(e));

        // Handle add position button
        addPositionBtn.addEventListener('click', () => this.addPosition());

        // Handle AI suggestions
        aiSuggestBtn.addEventListener('click', () => this.getAISuggestions());

        // Handle location type change
        document.querySelectorAll('input[name="locationType"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.toggleAddressField(e.target.value));
        });
    }

    // Initialize edit form
    initEditForm() {
        this.initCreateForm(); // Reuse create form functionality
        const form = document.getElementById('organizationForm');
        
        // Change submit handler for edit
        form.removeEventListener('submit', this.handleCreateSubmit);
        form.addEventListener('submit', (e) => this.handleEditSubmit(e));
    }

    // Handle create form submission
    async handleCreateSubmit(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBtn');
        const spinner = document.getElementById('submitSpinner');
        
        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const formData = this.collectFormData();
            const response = await axios.post('/api/organizations', formData);

            if (response.data.success) {
                this.showSuccess('Organization created successfully!');
                window.location.href = '/organizations';
            }

        } catch (error) {
            console.error('Error creating organization:', error);
            
            // Check if it's a moderation error
            if (error.response && error.response.data && error.response.data.error &&
                error.response.data.error.code === 'MODERATION_FAILED') {
                const moderationDetails = error.response.data.error.details;
                this.showModerationError(moderationDetails);
            } else {
                this.showError('Failed to create organization. Please try again.');
            }
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    // Handle edit form submission
    async handleEditSubmit(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBtn');
        const spinner = document.getElementById('submitSpinner');
        
        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const formData = this.collectFormData();
            const orgId = window.location.pathname.split('/')[2];
            const response = await axios.put(`/api/organizations/${orgId}`, formData);

            if (response.data.success) {
                this.showSuccess('Organization updated successfully!');
                window.location.href = `/organizations/${orgId}`;
            }

        } catch (error) {
            console.error('Error updating organization:', error);
            
            // Check if it's a moderation error
            if (error.response && error.response.data && error.response.data.error &&
                error.response.data.error.code === 'MODERATION_FAILED') {
                const moderationDetails = error.response.data.error.details;
                this.showModerationError(moderationDetails);
            } else {
                this.showError('Failed to update organization. Please try again.');
            }
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    // Collect form data
    collectFormData() {
        const formData = {
            name: document.getElementById('name').value,
            description: document.getElementById('description').value,
            website: document.getElementById('website').value,
            contactEmail: document.getElementById('contactEmail').value,
            logo: document.getElementById('logo').value,
            category: document.getElementById('category').value,
            tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(tag => tag),
            locationType: document.querySelector('input[name="locationType"]:checked').value,
            address: document.getElementById('address').value || '',
            openPositions: []
        };

        // Collect positions data
        const positionCards = document.querySelectorAll('.position-card');
        positionCards.forEach(card => {
            const position = {
                title: card.querySelector('input[name="positionTitle[]"]').value,
                applicationLink: card.querySelector('input[name="positionApplicationLink[]"]').value,
                description: card.querySelector('textarea[name="positionDescription[]"]').value,
                requirements: card.querySelector('input[name="positionRequirements[]"]').value.split(',').map(req => req.trim()).filter(req => req)
            };
            formData.openPositions.push(position);
        });

        return formData;
    }

    // Add position field
    addPosition(positionData = null) {
        const template = document.getElementById('positionTemplate');
        const clone = template.content.cloneNode(true);
        const positionCard = clone.querySelector('.position-card');
        const positionNumber = clone.querySelector('.position-number');
        
        const positionCount = document.querySelectorAll('.position-card').length + 1;
        positionNumber.textContent = positionCount;

        if (positionData) {
            const titleInput = clone.querySelector('input[name="positionTitle[]"]');
            const linkInput = clone.querySelector('input[name="positionApplicationLink[]"]');
            const descTextarea = clone.querySelector('textarea[name="positionDescription[]"]');
            const reqInput = clone.querySelector('input[name="positionRequirements[]"]');
            
            titleInput.value = positionData.title || '';
            linkInput.value = positionData.applicationLink || '';
            descTextarea.value = positionData.description || '';
            reqInput.value = positionData.requirements ? positionData.requirements.join(', ') : '';
        }

        // Add remove functionality
        const removeBtn = clone.querySelector('.remove-position');
        removeBtn.addEventListener('click', function() {
            positionCard.remove();
            organizationsManager.updatePositionNumbers();
        });

        document.getElementById('positionsContainer').appendChild(clone);
    }

    // Update position numbers after removal
    updatePositionNumbers() {
        const positionCards = document.querySelectorAll('.position-card');
        positionCards.forEach((card, index) => {
            const numberSpan = card.querySelector('.position-number');
            numberSpan.textContent = index + 1;
        });
    }

    // Toggle address field based on location type
    toggleAddressField(locationType) {
        const addressField = document.getElementById('addressField');
        if (locationType === 'onsite' || locationType === 'hybrid') {
            addressField.style.display = 'block';
        } else {
            addressField.style.display = 'none';
        }
    }

    // Get AI suggestions
    async getAISuggestions() {
        const orgName = document.getElementById('name').value;
        if (!orgName) {
            this.showError('Please enter an organization name first to get suggestions.');
            return;
        }

        const modal = new bootstrap.Modal(document.getElementById('aiSuggestionsModal'));
        modal.show();

        try {
            const response = await axios.post('/api/ai/suggestions', { name: orgName });
            const suggestions = response.data.data;

            document.getElementById('aiSuggestionsContent').innerHTML = `
                <div class="ai-suggestion">
                    <h6>Description Suggestion:</h6>
                    <p>${suggestions.description}</p>
                </div>
                <div class="ai-suggestion">
                    <h6>Tag Suggestions:</h6>
                    <p>${suggestions.tags.join(', ')}</p>
                </div>
                <div class="ai-suggestion">
                    <h6>Category Suggestion:</h6>
                    <p>${suggestions.category}</p>
                </div>
            `;

            // Setup apply suggestions button
            document.getElementById('applySuggestions').onclick = () => {
                document.getElementById('description').value = suggestions.description;
                document.getElementById('tags').value = suggestions.tags.join(', ');
                document.getElementById('category').value = suggestions.category;
                modal.hide();
            };

        } catch (error) {
            console.error('Error getting AI suggestions:', error);
            document.getElementById('aiSuggestionsContent').innerHTML = `
                <div class="alert alert-danger">
                    Failed to get AI suggestions. Please try again.
                </div>
            `;
        }
    }

    // Delete organization
    async deleteOrganization(orgId) {
        const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
        modal.show();

        document.getElementById('confirmDelete').onclick = async () => {
            try {
                const response = await axios.delete(`/api/organizations/${orgId}`);
                if (response.data.success) {
                    this.showSuccess('Organization deleted successfully!');
                    modal.hide();
                    this.loadUserOrganizations(); // Reload the list
                }
            } catch (error) {
                console.error('Error deleting organization:', error);
                this.showError('Failed to delete organization. Please try again.');
            }
        };
    }

    // Helper methods
    getCurrentUser() {
        // Placeholder - in real implementation, use Firebase Auth
        // This would return the current authenticated user
        return { uid: 'user123' }; // Mock user ID
    }

    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        alert('Error: ' + message);
    }

    showSuccess(message) {
        // Simple success display
        alert('Success: ' + message);
    }

    // Show moderation error with detailed feedback
    showModerationError(moderationDetails) {
        const alert = document.getElementById('moderationErrorAlert');
        const summary = document.getElementById('moderationErrorSummary');
        const details = document.getElementById('moderationErrorDetails');
        
        if (!alert || !summary || !details) {
            // Fallback to simple alert if elements not found
            this.showError('Moderation failed: ' + (moderationDetails.moderation_notes || 'Content contains inappropriate material'));
            return;
        }
        
        // Set summary message
        summary.textContent = moderationDetails.moderation_notes || 'Content moderation failed';
        
        // Build details list
        details.innerHTML = '';
        if (moderationDetails.reasons && moderationDetails.reasons.length > 0) {
            const ul = document.createElement('ul');
            moderationDetails.reasons.forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                ul.appendChild(li);
            });
            details.appendChild(ul);
        }
        
        // Show suggested changes if available
        if (moderationDetails.suggested_changes && moderationDetails.suggested_changes.length > 0) {
            const suggestions = document.createElement('div');
            suggestions.innerHTML = '<strong>Suggested changes:</strong>';
            const ul = document.createElement('ul');
            moderationDetails.suggested_changes.forEach(change => {
                const li = document.createElement('li');
                li.textContent = change;
                ul.appendChild(li);
            });
            suggestions.appendChild(ul);
            details.appendChild(suggestions);
        }
        
        // Show the alert
        alert.classList.remove('d-none');
        
        // Scroll to the alert
        alert.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Initialize organizations manager
const organizationsManager = new OrganizationsManager();

// Global function for delete confirmation (used in HTML onclick)
window.deleteOrganization = (orgId) => {
    organizationsManager.deleteOrganization(orgId);
};