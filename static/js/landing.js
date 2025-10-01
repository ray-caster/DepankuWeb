// --- static/js/landing.js ---

document.addEventListener('DOMContentLoaded', function () {
    setupEventListeners();
    setupMobileMenu();
});

function setupEventListeners() {
    // Handle clicks on popular tags to redirect to the main search page
    const popularTags = document.querySelectorAll('.popular-tags .tag');
    popularTags.forEach(tag => {
        tag.addEventListener('click', function () {
            const query = this.textContent.trim();
            window.location.href = `/organizations?search=${encodeURIComponent(query)}`;
        });
    });

    // Handle AI Analysis button click
    const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
    if (aiAnalysisBtn) {
        aiAnalysisBtn.addEventListener('click', function (e) {
            e.preventDefault();
            // This relies on the global 'auth' object from auth.js
            if (window.auth && window.auth.currentUser) {
                window.location.href = '/ai/analysis';
            } else {
                // Store the intended destination to redirect after signing up
                sessionStorage.setItem('redirectAfterSignup', '/ai/analysis');
                window.location.href = '/signup';
            }
        });
    }

    // Handle Create Organization button click
    const createOrgBtn = document.getElementById('create-org-btn');
    if (createOrgBtn) {
        createOrgBtn.addEventListener('click', function (e) {
            e.preventDefault();
            if (window.auth && window.auth.currentUser) {
                window.location.href = this.href;
            } else {
                sessionStorage.setItem('redirectAfterSignup', this.href);
                window.location.href = '/signup';
            }
        });
    }
}

function setupMobileMenu() {
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (!mobileMenuToggle || !navLinks) return;

    const menuIcon = mobileMenuToggle.querySelector('.menu-icon');
    const closeIcon = mobileMenuToggle.querySelector('.close-icon');

    mobileMenuToggle.addEventListener('click', function () {
        const isActive = navLinks.classList.toggle('active');
        mobileMenuToggle.setAttribute('aria-expanded', isActive);
        if (menuIcon && closeIcon) {
            menuIcon.style.display = isActive ? 'none' : 'inline';
            closeIcon.style.display = isActive ? 'inline' : 'none';
        }
    });
}