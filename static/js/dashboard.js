// Dashboard JavaScript - Drag-drop planning functionality
document.addEventListener('DOMContentLoaded', function () {
    // Initialize dashboard
    initializeDashboard();
});

// Global variables
let currentUser = null;
let userPlanningData = { organizations: [] };
let userOrganizations = []; // This will be the source of truth for orgs owned by the user

// Initialize dashboard
async function initializeDashboard() {
    try {
        currentUser = await window.authHandlers.getCurrentUser();
        if (!currentUser) {
            window.location.href = '/login'; // Redirect if not logged in
            return;
        }

        // Parallel fetch for planning data and user's owned organizations
        await Promise.all([
            loadPlanningData(),
            loadUserOwnedOrganizations()
        ]);

        // Initialize drag-drop functionality
        initializeDragDrop();
        updateDashboardUI();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError('Failed to load dashboard data. Please refresh the page.');
    }
}

// Load user planning data from our backend
async function loadPlanningData() {
    try {
        // FIX: Corrected the API endpoint from '/api/user/planning' to the one defined in dashboard.py
        const response = await fetch('/dashboard/api/planning');
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

// Load organizations created by the user from our backend
async function loadUserOwnedOrganizations() {
    try {
        // In a real app, this would be an API call like `/api/organizations?ownerId=${currentUser.uid}`
        // For now, we simulate this by filtering the combined list later.
        // This function will primarily populate the "Available Organizations" list.
        const response = await fetch('/api/organizations'); // Fetching a general list for demo
        const data = await response.json();
        if (data.success) {
            // Filter for organizations owned by the current user
            userOrganizations = data.data.filter(org => org.ownerId === currentUser.uid);
        } else {
            throw new Error(data.error.message);
        }
    } catch (error) {
        console.error('Error loading organizations:', error);
        throw error;
    }
}

// Initialize drag-drop functionality
function initializeDragDrop() {
    const columnContents = document.querySelectorAll('.column-content');
    columnContents.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragenter', handleDragEnter);
        column.addEventListener('dragleave', handleDragLeave);
    });

    const availableOrgs = document.getElementById('available-orgs');
    if (availableOrgs) {
        availableOrgs.addEventListener('dragover', handleDragOver);
        availableOrgs.addEventListener('drop', handleDrop);
    }
}

// Drag and drop event handlers
function handleDragStart(event) {
    if (event.target.dataset.orgId) {
        event.dataTransfer.setData('text/plain', event.target.dataset.orgId);
        event.target.classList.add('dragging');
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function handleDrop(event) {
    event.preventDefault();
    const orgId = event.dataTransfer.getData('text/plain');
    const droppedOnColumn = event.currentTarget;
    const interestLevel = droppedOnColumn.dataset.interestLevel; // e.g., 'high', 'medium', 'low', or 'none'

    updateOrganizationInterest(orgId, interestLevel);
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}

function handleDragEnter(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

// Update organization interest level in the backend
async function updateOrganizationInterest(orgId, newInterestLevel) {
    try {
        // Find if the org is already in the planning data
        let plannedOrg = userPlanningData.organizations.find(org => org.orgId === orgId);

        if (plannedOrg) {
            if (newInterestLevel === 'none') {
                // Remove from planning board
                userPlanningData.organizations = userPlanningData.organizations.filter(org => org.orgId !== orgId);
            } else {
                // Update interest level
                plannedOrg.interestLevel = newInterestLevel;
            }
        } else if (newInterestLevel !== 'none') {
            // Add new org to the planning board
            userPlanningData.organizations.push({
                orgId: orgId,
                interestLevel: newInterestLevel,
                notes: '',
                addedDate: new Date().toISOString()
            });
        } else {
            return; // Dropped into "available" from "available", no change.
        }

        const response = await fetch('/dashboard/api/planning', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ organizations: userPlanningData.organizations })
        });
        const data = await response.json();
        if (!data.success) throw new Error(data.error.message);

        showSuccess('Planning board updated!');
        updateDashboardUI();

    } catch (error) {
        console.error('Error updating organization interest:', error);
        showError('Failed to update planning board.');
    }
}

// Update the entire dashboard UI
function updateDashboardUI() {
    updatePlanningBoard();
    updateAvailableOrganizationsList();
    updateStatistics();
}

function updatePlanningBoard() {
    const columns = {
        high: document.querySelector('[data-interest-level="high"]'),
        medium: document.querySelector('[data-interest-level="medium"]'),
        low: document.querySelector('[data-interest-level="low"]'),
    };

    // Clear columns
    Object.values(columns).forEach(col => col.innerHTML = '<div class="empty-state"><p>Drop here</p></div>');

    const plannedOrgIds = new Set(userPlanningData.organizations.map(o => o.orgId));

    // Create a combined list of all orgs (owned + planned) to get full details
    const allKnownOrgs = [...userOrganizations];
    // This is a placeholder for fetching details of planned orgs not owned by the user
    // In a real app, you'd fetch details for any orgId in `userPlanningData` not in `userOrganizations`.

    userPlanningData.organizations.forEach(plannedOrg => {
        const orgDetails = allKnownOrgs.find(o => o.id === plannedOrg.orgId);
        if (orgDetails) {
            const orgCard = createOrganizationCard(orgDetails);
            const targetColumn = columns[plannedOrg.interestLevel];
            if (targetColumn) {
                if (targetColumn.querySelector('.empty-state')) {
                    targetColumn.innerHTML = ''; // Clear empty state
                }
                targetColumn.appendChild(orgCard);
            }
        }
    });

    // Update counts
    document.getElementById('high-count').textContent = userPlanningData.organizations.filter(o => o.interestLevel === 'high').length;
    document.getElementById('medium-count').textContent = userPlanningData.organizations.filter(o => o.interestLevel === 'medium').length;
    document.getElementById('low-count').textContent = userPlanningData.organizations.filter(o => o.interestLevel === 'low').length;
}


function updateAvailableOrganizationsList() {
    const availableContainer = document.getElementById('available-orgs');
    availableContainer.innerHTML = '';

    const plannedOrgIds = new Set(userPlanningData.organizations.map(o => o.orgId));

    const availableOrganizations = userOrganizations.filter(org => !plannedOrgIds.has(org.id));

    if (availableOrganizations.length === 0) {
        availableContainer.innerHTML = '<div class="empty-state"><p>No available organizations to plan.</p></div>';
    } else {
        availableOrganizations.forEach(org => {
            const orgCard = createOrganizationCard(org);
            availableContainer.appendChild(orgCard);
        });
    }
}

function updateStatistics() {
    const totalOrgs = userOrganizations.length;
    const highInterest = userPlanningData.organizations.filter(o => o.interestLevel === 'high').length;
    const mediumInterest = userPlanningData.organizations.filter(o => o.interestLevel === 'medium').length;
    const lowInterest = userPlanningData.organizations.filter(o => o.interestLevel === 'low').length;

    document.getElementById('total-orgs').textContent = totalOrgs;
    document.getElementById('high-interest').textContent = highInterest;
    document.getElementById('medium-interest').textContent = mediumInterest;
    document.getElementById('low-interest').textContent = lowInterest;
}

// Create organization card element
function createOrganizationCard(org) {
    const card = document.createElement('div');
    card.className = 'org-card';
    card.draggable = true;
    card.dataset.orgId = org.id;
    card.addEventListener('dragstart', handleDragStart);

    const interestBadgeClass = org.interestLevel ? org.interestLevel.split('_')[0] : '';
    const interestText = org.interestLevel ? org.interestLevel.replace('_', ' ') : '';

    card.innerHTML = `
        <div class="org-card-header">
            <h4 class="org-name">${org.name || 'Unnamed Organization'}</h4>
            ${org.interestLevel ? `<span class="org-interest-badge ${interestBadgeClass}">${interestText}</span>` : ''}
        </div>
        <div class="org-description">${org.description ? org.description.substring(0, 80) + '...' : 'No description.'}</div>
        <div class="org-tags">
            ${(org.tags || []).slice(0, 2).map(tag => `<span class="tag">${tag}</span>`).join('')}
        </div>
    `;
    return card;
}


// Utility functions for feedback
function showSuccess(message) {
    const el = document.getElementById('success-message');
    if (!el) return;
    el.textContent = message;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
}

function showError(message) {
    const el = document.getElementById('error-message');
    if (!el) return;
    el.textContent = message;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 5000);
}