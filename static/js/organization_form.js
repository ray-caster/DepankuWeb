let isEditMode = false;
let organizationId = null;

// --- INITIALIZATION ---
function initializeFormForCreate() {
    isEditMode = false;
    document.getElementById('form-title').textContent = 'Create a New Organization';
    document.getElementById('submitBtn').textContent = 'Submit for Review';
    setupCommonEventListeners();
    addPosition(); // Add one empty position card by default
    document.getElementById('loading-container').style.display = 'none';
    document.getElementById('form-container').style.display = 'block';
}

async function initializeFormForEdit(orgId) {
    isEditMode = true;
    organizationId = orgId;
    document.getElementById('form-title').textContent = 'Edit Organization';
    document.getElementById('submitBtn').textContent = 'Save Changes';
    setupCommonEventListeners();
    await loadOrganizationDataForEdit();
}

// --- EVENT LISTENERS ---
function setupCommonEventListeners() {
    document.getElementById('organizationForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('addPositionBtn').addEventListener('click', () => addPosition());

    document.querySelectorAll('input[name="locationType"]').forEach(radio => {
        radio.addEventListener('change', (e) => toggleAddressField(e.target.value));
    });
}

// --- DATA HANDLING ---
async function loadOrganizationDataForEdit() {
    const loadingEl = document.getElementById('loading-container');
    const formEl = document.getElementById('form-container');
    try {
        const response = await fetch(`/api/organizations/${organizationId}`);
        if (!response.ok) throw new Error('Failed to fetch organization data.');
        const result = await response.json();
        if (!result.success) throw new Error(result.error.message);

        populateForm(result.data);
        loadingEl.style.display = 'none';
        formEl.style.display = 'block';
    } catch (error) {
        loadingEl.innerHTML = `<p class="alert alert-danger">${error.message}</p>`;
    }
}

function populateForm(org) {
    document.getElementById('name').value = org.name || '';
    document.getElementById('description').value = org.description || '';
    document.getElementById('category').value = org.category || '';
    document.getElementById('tags').value = (org.tags || []).join(', ');
    document.getElementById('website').value = org.website || '';
    document.getElementById('contactEmail').value = org.contactEmail || '';
    document.getElementById('logo').value = org.logo || '';

    const locationType = org.location?.type || 'remote';
    document.querySelector(`input[name="locationType"][value="${locationType}"]`).checked = true;
    toggleAddressField(locationType);
    document.getElementById('address').value = org.location?.address || '';

    document.getElementById('positionsContainer').innerHTML = ''; // Clear default
    if (org.openPositions && org.openPositions.length > 0) {
        org.openPositions.forEach(pos => addPosition(pos));
    } else {
        addPosition(); // Add one empty if none exist
    }
}

function collectFormData() {
    // *** THIS IS THE CRITICAL CORRECTION ***
    // The location data is now nested in an object to match the backend.
    const formData = {
        name: document.getElementById('name').value.trim(),
        description: document.getElementById('description').value.trim(),
        category: document.getElementById('category').value,
        tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(Boolean),
        website: document.getElementById('website').value.trim(),
        contactEmail: document.getElementById('contactEmail').value.trim(),
        logo: document.getElementById('logo').value.trim(),
        location: {
            type: document.querySelector('input[name="locationType"]:checked').value,
            address: document.getElementById('address').value.trim()
        },
        openPositions: []
    };

    document.querySelectorAll('#positionsContainer .position-card').forEach(card => {
        const title = card.querySelector('.position-title').value.trim();
        // Only add position if a title is provided
        if (title) {
            formData.openPositions.push({
                title: title,
                description: card.querySelector('.position-description').value.trim(),
                requirements: card.querySelector('.position-requirements').value.split(',').map(req => req.trim()).filter(Boolean),
                applicationLink: card.querySelector('.position-link').value.trim()
            });
        }
    });
    return formData;
}

// --- FORM SUBMISSION ---
async function handleFormSubmit(event) {
    event.preventDefault();
    const submitBtn = document.getElementById('submitBtn');
    setButtonLoading(submitBtn, true, isEditMode ? 'Saving...' : 'Submitting...');
    hideModerationError();

    const formData = collectFormData();
    const url = isEditMode ? `/api/organizations/${organizationId}` : '/api/organizations';
    const method = isEditMode ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        const result = await response.json();

        // Use response.status to check for non-2xx codes which fetch doesn't throw by default
        if (!response.ok) {
            // Give the 'error' object from the JSON body to the catch block
            throw result.error || new Error(`Request failed with status ${response.status}`);
        }

        // 202 Accepted (moderation task started) is also a success
        if (response.status === 200 || response.status === 201 || response.status === 202) {
            const viewUrl = `/organizations/${result.data.id || organizationId}`;
            // Redirect to the view page after a short delay to show success
            window.location.href = viewUrl;
        } else {
            throw new Error('An unexpected response was received from the server.');
        }

    } catch (error) {
        if (error.code === 'MODERATION_FAILED') {
            showModerationError(error.details);
        } else {
            showError(error.message || 'An unknown error occurred. Please try again.');
        }
        setButtonLoading(submitBtn, false, isEditMode ? 'Save Changes' : 'Submit for Review');
    }
}

// --- DYNAMIC FORM ELEMENTS (POSITIONS) ---
function addPosition(data = {}) {
    const container = document.getElementById('positionsContainer');
    const template = document.getElementById('positionTemplate');
    const clone = template.content.cloneNode(true);
    const card = clone.querySelector('.position-card');

    if (data.title) card.querySelector('.position-title').value = data.title;
    if (data.description) card.querySelector('.position-description').value = data.description;
    if (data.requirements) card.querySelector('.position-requirements').value = data.requirements.join(', ');
    if (data.applicationLink) card.querySelector('.position-link').value = data.applicationLink;

    card.querySelector('.remove-position').addEventListener('click', () => {
        card.remove();
        updatePositionNumbers();
    });

    container.appendChild(clone);
    updatePositionNumbers();
}

function updatePositionNumbers() {
    document.querySelectorAll('#positionsContainer .position-card').forEach((card, index) => {
        card.querySelector('.position-number').textContent = index + 1;
    });
}

// --- UI UTILITIES ---
function toggleAddressField(locationType) {
    document.getElementById('addressField').style.display = ['hybrid', 'onsite'].includes(locationType) ? 'block' : 'none';
}

function showError(message) {
    const alertEl = document.getElementById('generalErrorAlert');
    alertEl.textContent = message;
    alertEl.style.display = 'block';
    alertEl.scrollIntoView({ behavior: 'smooth' });
}

function showModerationError(details) {
    const alertEl = document.getElementById('moderationErrorAlert');
    const summaryEl = document.getElementById('moderationErrorSummary');
    const detailsEl = document.getElementById('moderationErrorDetails');

    summaryEl.textContent = details?.moderation_notes || 'Content violates community guidelines.';
    detailsEl.innerHTML = '<strong>Reasons:</strong><ul>' + (details?.reasons || ['N/A']).map(r => `<li>${r}</li>`).join('') + '</ul>';
    alertEl.style.display = 'block';
    alertEl.scrollIntoView({ behavior: 'smooth' });
}

function hideModerationError() {
    document.getElementById('moderationErrorAlert').style.display = 'none';
    document.getElementById('generalErrorAlert').style.display = 'none';
}

function setButtonLoading(button, isLoading, loadingText) {
    const originalText = button.dataset.originalText || button.textContent;
    if (isLoading) {
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.textContent;
        }
        button.disabled = true;
        button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
    } else {
        button.disabled = false;
        button.innerHTML = originalText;
        delete button.dataset.originalText;
    }
}