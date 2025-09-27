// Dashboard JavaScript - Drag-drop planning functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();
});

// Global variables
let currentUser = null;
let userPlanningData = null;
let userOrganizations = [];
let userProfileData = null;

// Initialize dashboard
async function initializeDashboard() {
    try {
        // Get current user
        currentUser = await window.authHandlers.getCurrentUser();
        if (!currentUser) {
            window.location.href = '/login';
            return;
        }

        // Load user profile data
        await loadUserProfile();

        // Load user planning data
        await loadPlanningData();

        // Load user organizations
        await loadOrganizations();

        // Initialize drag-drop functionality
        initializeDragDrop();

        // Update UI with loaded data
        updateDashboardUI();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError('Failed to load dashboard data');
    }
}

// Load user profile data
async function loadUserProfile() {
    try {
        const response = await fetch(`/api/auth/profile?uid=${currentUser.uid}`);
        const data = await response.json();
        
        if (data.success) {
            userProfileData = data.data;
        } else {
            throw new Error(data.error.message);
        }
    } catch (error) {
        console.error('Error loading user profile:', error);
        throw error;
    }
}

// Load user planning data
async function loadPlanningData() {
    try {
        const response = await fetch(`/api/user/planning?uid=${currentUser.uid}`);
        const data = await response.json();
        
        if (data.success) {
            userPlanningData = data.data;
        } else {
            throw new Error(data.error.message);
        }
    } catch (error) {
        console.error('Error loading planning data:', error);
        throw error;
    }
}

// Load user organizations from Firestore
async function loadOrganizations() {
    try {
        // Get organizations where user is owner
        const organizationsRef = firebase.firestore().collection('organizations');
        const snapshot = await organizationsRef
            .where('ownerId', '==', currentUser.uid)
            .where('status', '==', 'approved')
            .get();
        
        userOrganizations = [];
        snapshot.forEach(doc => {
            const orgData = doc.data();
            userOrganizations.push({
                id: doc.id,
                ...orgData
            });
        });

        // Also get organizations from planning data to include those that might not be owned by user
        if (userPlanningData && userPlanningData.organizations) {
            const plannedOrgs = userPlanningData.organizations;
            for (const plannedOrg of plannedOrgs) {
                // Check if we already have this organization
                const exists = userOrganizations.find(org => org.id === plannedOrg.orgId);
                if (!exists) {
                    // Fetch organization details
                    try {
                        const orgDoc = await organizationsRef.doc(plannedOrg.orgId).get();
                        if (orgDoc.exists) {
                            const orgData = orgDoc.data();
                            userOrganizations.push({
                                id: orgDoc.id,
                                ...orgData,
                                interestLevel: plannedOrg.interestLevel,
                                notes: plannedOrg.notes,
                                position: plannedOrg.position
                            });
                        }
                    } catch (error) {
                        console.warn('Could not fetch organization:', plannedOrg.orgId, error);
                    }
                }
            }
        }

    } catch (error) {
        console.error('Error loading organizations:', error);
        throw error;
    }
}

// Initialize drag-drop functionality
function initializeDragDrop() {
    // Add event listeners to all column content areas
    const columnContents = document.querySelectorAll('.column-content');
    columnContents.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragenter', handleDragEnter);
        column.addEventListener('dragleave', handleDragLeave);
    });

    // Add event listener to logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', window.authHandlers.handleLogout);
    }
}

// Drag and drop event handlers
function handleDragStart(event) {
    event.dataTransfer.setData('text/plain', event.target.dataset.orgId);
    event.target.classList.add('dragging');
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function handleDrop(event) {
    event.preventDefault();
    const orgId = event.dataTransfer.getData('text/plain');
    const column = event.currentTarget;
    const interestLevel = column.closest('.board-column').id.replace('-column', '').replace('-', '_');
    
    // Update organization interest level
    updateOrganizationInterest(orgId, interestLevel);
    
    // Remove drag over styling
    column.classList.remove('drag-over');
}

function handleDragEnter(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

// Update organization interest level
async function updateOrganizationInterest(orgId, interestLevel) {
    try {
        // Find the organization
        const orgIndex = userOrganizations.findIndex(org => org.id === orgId);
        if (orgIndex === -1) return;

        // Update local data
        userOrganizations[orgIndex].interestLevel = interestLevel;

        // Update planning data structure
        const planningOrgs = userOrganizations
            .filter(org => org.interestLevel)
            .map(org => ({
                orgId: org.id,
                interestLevel: org.interestLevel,
                notes: org.notes || '',
                addedDate: org.addedDate || new Date(),
                position: org.position || 0
            }));

        // Send update to backend
        const response = await fetch(`/api/user/planning?uid=${currentUser.uid}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                organizations: planningOrgs
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // Update UI
            updateDashboardUI();
            showSuccess('Organization moved successfully');
        } else {
            throw new Error(data.error.message);
        }

    } catch (error) {
        console.error('Error updating organization interest:', error);
        showError('Failed to update organization');
    }
}

// Update dashboard UI with loaded data
function updateDashboardUI() {
    // Update profile summary
    updateProfileSummary();

    // Update planning board
    updatePlanningBoard();

    // Update organization lists
    updateOrganizationLists();

    // Update statistics
    updateStatistics();
}

// Update profile summary
function updateProfileSummary() {
    if (!userProfileData) return;

    const userName = document.getElementById('user-name');
    const userAge = document.getElementById('user-age');
    const userInterests = document.getElementById('user-interests');

    if (userName) userName.textContent = userProfileData.displayName || 'Not set';
    if (userAge) userAge.textContent = userProfileData.ageGroup || 'Not set';
    
    if (userInterests && userProfileData.preferences && userProfileData.preferences.interests) {
        userInterests.textContent = userProfileData.preferences.interests.join(', ') || 'None';
    }
}

// Update planning board
function updatePlanningBoard() {
    // Clear all columns
    const highColumn = document.getElementById('high-interest-column').querySelector('.column-content');
    const mediumColumn = document.getElementById('medium-interest-column').querySelector('.column-content');
    const lowColumn = document.getElementById('low-interest-column').querySelector('.column-content');
    
    highColumn.innerHTML = '<div class="empty-state" id="high-empty"><p>Drop organizations here</p></div>';
    mediumColumn.innerHTML = '<div class="empty-state" id="medium-empty"><p>Drop organizations here</p></div>';
    lowColumn.innerHTML = '<div class="empty-state" id="low-empty"><p>Drop organizations here</p></div>';

    // Count organizations by interest level
    let highCount = 0;
    let mediumCount = 0;
    let lowCount = 0;

    // Add organizations to their respective columns
    userOrganizations.forEach(org => {
        if (!org.interestLevel) return;

        const orgCard = createOrganizationCard(org);
        
        switch (org.interestLevel) {
            case 'high_interest':
                highColumn.appendChild(orgCard);
                highCount++;
                break;
            case 'medium_interest':
                mediumColumn.appendChild(orgCard);
                mediumCount++;
                break;
            case 'low_interest':
                lowColumn.appendChild(orgCard);
                lowCount++;
                break;
        }
    });

    // Update column counts
    document.getElementById('high-count').textContent = highCount;
    document.getElementById('medium-count').textContent = mediumCount;
    document.getElementById('low-count').textContent = lowCount;

    // Hide empty states if column has items
    if (highCount > 0) document.getElementById('high-empty').style.display = 'none';
    if (mediumCount > 0) document.getElementById('medium-empty').style.display = 'none';
    if (lowCount > 0) document.getElementById('low-empty').style.display = 'none';
}

// Create organization card element
function createOrganizationCard(org) {
    const template = document.getElementById('org-card-template');
    const card = template.content.cloneNode(true).querySelector('.org-card');
    
    // Set organization data
    card.dataset.orgId = org.id;
    card.querySelector('.org-name').textContent = org.name || 'Unnamed Organization';
    card.querySelector('.org-description').textContent = org.description || 'No description available';
    card.querySelector('.org-id').value = org.id;
    card.querySelector('.org-interest').value = org.interestLevel || '';
    
    // Set interest badge
    const badge = card.querySelector('.org-interest-badge');
    if (org.interestLevel) {
        badge.textContent = org.interestLevel.replace('_', ' ').toUpperCase();
        badge.classList.add(org.interestLevel.split('_')[0]); // high, medium, low
    } else {
        badge.style.display = 'none';
    }
    
    // Set tags
    const tagsContainer = card.querySelector('.org-tags');
    if (org.tags && org.tags.length > 0) {
        org.tags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.textContent = tag;
            tagsContainer.appendChild(tagElement);
        });
    }
    
    // Set meta information
    const category = card.querySelector('.org-category');
    const location = card.querySelector('.org-location');
    
    if (category && org.category) category.textContent = org.category;
    if (location && org.location && org.location.type) {
        location.textContent = org.location.type.charAt(0).toUpperCase() + org.location.type.slice(1);
    }
    
    // Add drag event
    card.addEventListener('dragstart', handleDragStart);
    
    return card;
}

// Update organization lists
function updateOrganizationLists() {
    const availableOrgs = document.getElementById('available-orgs');
    const pastExperiences = document.getElementById('past-experiences');
    const currentOpportunities = document.getElementById('current-opportunities');
    
    // Clear existing content
    availableOrgs.innerHTML = '';
    pastExperiences.innerHTML = '';
    currentOpportunities.innerHTML = '';
    
    // Add organizations without interest level to available organizations
    const availableOrganizations = userOrganizations.filter(org => !org.interestLevel);
    
    if (availableOrganizations.length === 0) {
        availableOrgs.innerHTML = '<div class="empty-state"><p>No available organizations</p></div>';
    } else {
        availableOrganizations.forEach(org => {
            const orgCard = createOrganizationCard(org);
            availableOrgs.appendChild(orgCard);
        });
    }
    
    // Placeholder for past experiences and current opportunities
    // These would typically be filtered by status or dates
    pastExperiences.innerHTML = '<div class="empty-state"><p>No past experiences yet</p></div>';
    currentOpportunities.innerHTML = '<div class="empty-state"><p>No current opportunities yet</p></div>';
}

// Update statistics
function updateStatistics() {
    const totalOrgs = userOrganizations.length;
    const highInterest = userOrganizations.filter(org => org.interestLevel === 'high_interest').length;
    const mediumInterest = userOrganizations.filter(org => org.interestLevel === 'medium_interest').length;
    const lowInterest = userOrganizations.filter(org => org.interestLevel === 'low_interest').length;
    
    document.getElementById('total-orgs').textContent = totalOrgs;
    document.getElementById('high-interest').textContent = highInterest;
    document.getElementById('medium-interest').textContent = mediumInterest;
    document.getElementById('low-interest').textContent = lowInterest;
}

// Utility functions
function showSuccess(message) {
    // Create or show success message
    let successElement = document.getElementById('success-message');
    if (!successElement) {
        successElement = document.createElement('div');
        successElement.id = 'success-message';
        successElement.className = 'success-message';
        document.querySelector('.dashboard-section').prepend(successElement);
    }
    
    successElement.textContent = message;
    setTimeout(() => {
        successElement.style.display = 'none';
    }, 3000);
}

function showError(message) {
    // Create or show error message
    let errorElement = document.getElementById('error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = 'error-message';
        errorElement.className = 'error-message';
        document.querySelector('.dashboard-section').prepend(errorElement);
    }
    
    errorElement.textContent = message;
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

// Make functions available for HTML5 drag-drop API
function drag(event) {
    handleDragStart(event);
}

function allowDrop(event) {
    handleDragOver(event);
}

function drop(event) {
    handleDrop(event);
}