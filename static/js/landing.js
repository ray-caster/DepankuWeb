// Depanku Landing Page JavaScript - Enhanced Mobile Responsiveness

// Firebase configuration (will be loaded from firebase_config.json)
let firebaseApp;
let auth;

// Initialize Firebase
function initializeFirebase() {
    fetch('/static/firebase_config.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Firebase config not found');
            }
            return response.json();
        })
        .then(config => {
            try {
                firebaseApp = firebase.initializeApp(config);
                auth = firebaseApp.auth();
                console.log('Firebase initialized for landing page');
                
                // Check authentication state and update UI
                checkAuthState();
            } catch (error) {
                console.error('Firebase initialization error:', error);
                // Fallback: proceed without Firebase for landing page
                updateUIForUnauthenticatedUser();
            }
        })
        .catch(error => {
            console.error('Error loading Firebase config:', error);
            // Fallback: proceed without Firebase for landing page
            updateUIForUnauthenticatedUser();
        });
}

// Check authentication state and update UI
function checkAuthState() {
    if (!auth) return;
    
    auth.onAuthStateChanged((user) => {
        if (user) {
            // User is signed in
            console.log('User signed in:', user.email);
            updateUIForAuthenticatedUser();
        } else {
            // User is signed out
            console.log('User signed out');
            updateUIForUnauthenticatedUser();
        }
    });
}

// Update UI for authenticated user
function updateUIForAuthenticatedUser() {
    // Update navigation
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.innerHTML = `
            <a href="#features" class="nav-link">Features</a>
            <a href="#how-it-works" class="nav-link">How It Works</a>
            <a href="/profile" class="nav-link">Profile</a>
            <a href="#" class="btn btn-secondary" id="logout-btn">Logout</a>
        `;
        
        // Add logout event listener
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }
    }
    
    // Update CTA buttons
    const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
    if (aiAnalysisBtn) {
        aiAnalysisBtn.textContent = '🤖 Start AI Analysis';
        aiAnalysisBtn.href = '/ai-analysis';
    }
    
    const createOrgBtn = document.getElementById('create-org-btn');
    if (createOrgBtn) {
        createOrgBtn.href = '/organizations/create';
    }
}

// Update UI for unauthenticated user
function updateUIForUnauthenticatedUser() {
    // Update navigation
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.innerHTML = `
            <a href="#features" class="nav-link">Features</a>
            <a href="#how-it-works" class="nav-link">How It Works</a>
            <a href="/login" class="nav-link">Login</a>
            <a href="/signup" class="btn btn-secondary">Sign Up</a>
        `;
    }
    
    // Update CTA buttons
    const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
    if (aiAnalysisBtn) {
        aiAnalysisBtn.textContent = '🤖 Get AI Analysis';
        aiAnalysisBtn.href = '/signup';
    }
    
    const createOrgBtn = document.getElementById('create-org-btn');
    if (createOrgBtn) {
        createOrgBtn.href = '/signup';
    }
}

// Handle logout
function handleLogout(event) {
    event.preventDefault();
    
    if (auth) {
        auth.signOut()
            .then(() => {
                console.log('User signed out');
                window.location.href = '/';
            })
            .catch((error) => {
                console.error('Logout error:', error);
            });
    }
}

// Initialize Algolia Search Client (placeholder - remove or configure properly)
let algoliaClient = null;
let index = null;

function initializeAlgolia() {
    // Check if Algolia is configured
    if (typeof algoliasearch === 'undefined') {
        console.warn('Algolia search is not available');
        return;
    }
    
    try {
        // Use environment variables or configuration for credentials
        const appId = window.ALGOLIA_APP_ID || 'YOUR_ALGOLIA_APP_ID';
        const apiKey = window.ALGOLIA_SEARCH_API_KEY || 'YOUR_ALGOLIA_SEARCH_API_KEY';
        
        if (appId === 'YOUR_ALGOLIA_APP_ID' || apiKey === 'YOUR_ALGOLIA_SEARCH_API_KEY') {
            console.warn('Algolia credentials not configured. Search functionality disabled.');
            return;
        }
        
        algoliaClient = algoliasearch(appId, apiKey);
        index = algoliaClient.initIndex('organizations');
        console.log('Algolia search initialized');
    } catch (error) {
        console.error('Algolia initialization error:', error);
    }
}

// DOM Elements
const searchInput = document.querySelector('.search-input');
const searchBtn = document.querySelector('.search-btn');
const popularTags = document.querySelectorAll('.tag');
const searchBox = document.getElementById('search-box');
const createOrgBtn = document.getElementById('create-org-btn');
const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const menuIcon = mobileMenuToggle?.querySelector('.menu-icon');
const closeIcon = mobileMenuToggle?.querySelector('.close-icon');

// Mobile Menu Functionality
function setupMobileMenu() {
    if (!mobileMenuToggle) return;
    
    const navLinks = document.querySelector('.nav-links');
    
    mobileMenuToggle.addEventListener('click', function() {
        navLinks.classList.toggle('active');
        const isActive = navLinks.classList.contains('active');
        
        // Update aria-expanded attribute
        mobileMenuToggle.setAttribute('aria-expanded', isActive);
        
        // Toggle menu icons
        if (isActive) {
            menuIcon.style.display = 'none';
            closeIcon.style.display = 'inline';
        } else {
            menuIcon.style.display = 'inline';
            closeIcon.style.display = 'none';
        }
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
        if (navLinks.classList.contains('active') &&
            !navLinks.contains(event.target) &&
            !mobileMenuToggle.contains(event.target)) {
            navLinks.classList.remove('active');
            mobileMenuToggle.setAttribute('aria-expanded', 'false');
            menuIcon.style.display = 'inline';
            closeIcon.style.display = 'none';
        }
    });
    
    // Close menu when clicking on nav links
    document.querySelectorAll('.nav-link, .btn').forEach(link => {
        link.addEventListener('click', function() {
            navLinks.classList.remove('active');
            mobileMenuToggle.setAttribute('aria-expanded', 'false');
            menuIcon.style.display = 'inline';
            closeIcon.style.display = 'none';
        });
    });
    
    // Handle keyboard navigation
    mobileMenuToggle.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            mobileMenuToggle.click();
        }
    });
}

// Algolia Autocomplete Instance (only initialize if Algolia is available)
function initializeAutocomplete() {
    if (!index) {
        // Fallback: basic search without Algolia
        console.log('Using fallback search functionality');
        return;
    }
    
    if (typeof autocomplete === 'undefined') {
        console.warn('Algolia autocomplete not available');
        return;
    }
    
    const autocompleteInstance = autocomplete({
        container: searchBox,
        placeholder: 'Search organizations, internships, or opportunities...',
        getSources({ query }) {
            return [
                {
                    sourceId: 'organizations',
                    getItems() {
                        return index.search(query).then(({ hits }) => hits);
                    },
                    templates: {
                        item({ item }) {
                            return `
                                <div class="aa-ItemWrapper">
                                    <div class="aa-ItemContent">
                                        <div class="aa-ItemIcon">
                                            <img src="${item.logo || '/static/images/default-org.png'}" alt="${item.name}" />
                                        </div>
                                        <div class="aa-ItemContentBody">
                                            <div class="aa-ItemContentTitle">
                                                ${item.name}
                                            </div>
                                            <div class="aa-ItemContentDescription">
                                                ${item.description || 'No description available'}
                                            </div>
                                            <div class="aa-ItemContentTags">
                                                ${item.tags ? item.tags.map(tag => `<span class="tag">${tag}</span>`).join('') : ''}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        },
                        noResults() {
                            return 'No organizations found. Try different keywords.';
                        }
                    }
                }
            ];
        }
    });
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    initializeFirebase();
    initializeAlgolia();
    initializeSearch();
    setupEventListeners();
    setupMobileMenu();
    applyPersuasiveLanguage();
    addMicroInteractions();
    initializeScarcityTimer();
    animateStatistics();
    addGamificationElements();
    enhanceUserPersonalization();
    initializeAutocomplete();
});

function initializeSearch() {
    // Set up search functionality
    if (searchInput && searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }

    // Set up popular tags click handlers
    popularTags.forEach(tag => {
        tag.addEventListener('click', function() {
            const tagText = this.textContent;
            searchInput.value = tagText;
            handleSearch();
        });
    });
}

function handleSearch() {
    const query = searchInput.value.trim();
    if (query) {
        // Check if user is authenticated
        if (auth && auth.currentUser) {
            // Redirect authenticated users to organizations page with search query
            window.location.href = `/organizations?search=${encodeURIComponent(query)}`;
        } else {
            // For unauthenticated users, redirect to signup with search query preserved
            const searchParams = new URLSearchParams();
            searchParams.set('search', query);
            window.location.href = `/signup?${searchParams.toString()}`;
        }
    }
}

function setupEventListeners() {
    // Create Organization Button - Persuasive action
    if (createOrgBtn) {
        createOrgBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (auth && auth.currentUser) {
                window.location.href = '/organizations/create';
            } else {
                window.location.href = '/signup';
            }
        });
    }

    // AI Analysis Button - Authentication handling
    if (aiAnalysisBtn) {
        aiAnalysisBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (auth && auth.currentUser) {
                window.location.href = '/ai-analysis';
            } else {
                window.location.href = '/signup';
            }
        });
    }
}

// Persuasive Language and Rhetorical Enhancements
function applyPersuasiveLanguage() {
    // Enhance the "Create Organization" button with rhetorical language
    if (createOrgBtn) {
        createOrgBtn.innerHTML = '🚀 Launch Your Organization & Make a Difference';
        createOrgBtn.title = 'Join educators and organizations helping students find their path';
    }

    // Add hover effects for persuasion (only on devices that support hover)
    if (window.matchMedia('(hover: hover)').matches) {
        const persuasiveElements = document.querySelectorAll('.btn-primary, .btn-secondary, .feature-card');
        persuasiveElements.forEach(element => {
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 8px 25px rgba(0, 123, 255, 0.3)';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
        });
    }
}

function addMicroInteractions() {
    // Add subtle animations to engage users
    const animatedElements = document.querySelectorAll('.feature-icon, .step-number, .testimonial-card');
    
    animatedElements.forEach((element, index) => {
        // Stagger animations for visual appeal
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Add scroll-triggered animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe elements for scroll animations
    document.querySelectorAll('.feature-card, .step, .testimonial-card').forEach(el => {
        observer.observe(el);
    });
}

// Touch device optimizations
function optimizeForTouch() {
    // Add touch-specific event listeners
    if ('ontouchstart' in window) {
        // Increase touch target sizes for better usability
        document.querySelectorAll('button, a, input, select, textarea').forEach(element => {
            if (element.offsetHeight < 44) {
                element.style.minHeight = '44px';
            }
            if (element.offsetWidth < 44 && element.tagName !== 'INPUT') {
                element.style.minWidth = '44px';
            }
        });
        
        // Add touch feedback
        document.querySelectorAll('.btn, .nav-link, .tag').forEach(element => {
            element.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            element.addEventListener('touchend', function() {
                this.style.transform = '';
            });
        });
    }
}

// Viewport height adjustment for mobile browsers
function adjustViewportHeight() {
    const setVh = () => {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    };
    
    setVh();
    window.addEventListener('resize', setVh);
    window.addEventListener('orientationchange', setVh);
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize additional mobile optimizations
document.addEventListener('DOMContentLoaded', function() {
    optimizeForTouch();
    adjustViewportHeight();
});

// Social Sharing Functions
function shareOnFacebook() {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    const description = encodeURIComponent(document.querySelector('meta[name="description"]')?.content || 'AI-powered organization discovery and career planning platform for students');
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}&quote=${title}: ${description}`, '_blank', 'width=600,height=400');
    trackSocialShare('facebook');
}

function shareOnTwitter() {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    const text = encodeURIComponent(`${title}: AI-powered platform helping students discover STEM internships and organizations! #CareerPlanning #STEM`);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank', 'width=600,height=400');
    trackSocialShare('twitter');
}

function shareOnLinkedIn() {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    const summary = encodeURIComponent(document.querySelector('meta[name="description"]')?.content || 'AI-powered platform helping students discover STEM internships, research opportunities, and organizations.');
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}&title=${title}&summary=${summary}`, '_blank', 'width=600,height=400');
    trackSocialShare('linkedin');
}

function shareOnWhatsApp() {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    const text = encodeURIComponent(`${title}: Check out Depanku - AI-powered organization discovery and career planning platform: ${url}`);
    window.open(`https://wa.me/?text=${text}`, '_blank', 'width=600,height=400');
    trackSocialShare('whatsapp');
}

// Scarcity Timer Implementation
function initializeScarcityTimer() {
    const timer = document.getElementById('countdown-timer');
    if (!timer) return;
    
    // Set countdown to 7 days from now
    const endDate = new Date();
    endDate.setDate(endDate.getDate() + 7);
    
    function updateTimer() {
        const now = new Date();
        const timeRemaining = endDate - now;
        
        if (timeRemaining <= 0) {
            // Reset timer when it expires
            endDate.setDate(endDate.getDate() + 7);
            return;
        }
        
        const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
        const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
        
        document.getElementById('days').textContent = days.toString().padStart(2, '0');
        document.getElementById('hours').textContent = hours.toString().padStart(2, '0');
        document.getElementById('minutes').textContent = minutes.toString().padStart(2, '0');
    }
    
    // Update immediately and set interval
    updateTimer();
    setInterval(updateTimer, 60000); // Update every minute
}

// Animated Statistics Counting
function animateStatistics() {
    const stats = [
        { id: 'stat-students', target: 15000, duration: 2000 },
        { id: 'stat-organizations', target: 500, duration: 1500 },
        { id: 'stat-success', target: 94, duration: 1000 },
        { id: 'stat-countries', target: 50, duration: 1200 }
    ];
    
    stats.forEach(stat => {
        const element = document.getElementById(stat.id);
        if (!element) return;
        
        const start = 0;
        const increment = stat.target / (stat.duration / 16); // 60fps
        
        let current = start;
        const timer = setInterval(() => {
            current += increment;
            if (current >= stat.target) {
                clearInterval(timer);
                element.textContent = stat.id === 'stat-success' ?
                    `${stat.target}%` : `${stat.target}+`;
            } else {
                element.textContent = stat.id === 'stat-success' ?
                    `${Math.floor(current)}%` : `${Math.floor(current)}+`;
            }
        }, 16);
    });
}

// Gamification Elements
function addGamificationElements() {
    // Add achievement badges based on user interactions
    const achievementBadges = [
        { id: 'first-visit', name: 'First Visit', icon: '🌟' },
        { id: 'explored-features', name: 'Feature Explorer', icon: '🔍' },
        { id: 'shared-platform', name: 'Social Sharer', icon: '📱' }
    ];
    
    // Check localStorage for achievements
    achievementBadges.forEach(badge => {
        if (!localStorage.getItem(badge.id)) {
            // Add event listeners to unlock achievements
            if (badge.id === 'first-visit') {
                localStorage.setItem(badge.id, 'true');
                showAchievementBadge(badge);
            }
        }
    });
    
    // Add scroll-based achievements
    window.addEventListener('scroll', function() {
        if (window.scrollY > 500 && !localStorage.getItem('explored-features')) {
            localStorage.setItem('explored-features', 'true');
            showAchievementBadge(achievementBadges[1]);
        }
    });
}

function showAchievementBadge(badge) {
    const badgeElement = document.createElement('div');
    badgeElement.className = 'achievement-badge';
    badgeElement.innerHTML = `
        <span class="badge-icon">${badge.icon}</span>
        <span class="badge-text">Unlocked: ${badge.name}</span>
    `;
    
    badgeElement.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, var(--primary-blue), var(--primary-green));
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 8px;
        animation: slideInRight 0.5s ease-out;
    `;
    
    document.body.appendChild(badgeElement);
    
    // Remove after 5 seconds
    setTimeout(() => {
        badgeElement.style.animation = 'slideOutRight 0.5s ease-in';
        setTimeout(() => badgeElement.remove(), 500);
    }, 5000);
}

// Enhanced User Personalization
function enhanceUserPersonalization() {
    // Time-based personalization
    const hour = new Date().getHours();
    let timeGreeting = '';
    
    if (hour < 12) timeGreeting = 'Good morning!';
    else if (hour < 18) timeGreeting = 'Good afternoon!';
    else timeGreeting = 'Good evening!';
    
    // Update hero text with personalized greeting
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        heroTitle.innerHTML = `Depanku: ${timeGreeting} AI-Powered Career Platform`;
    }
    
    // Location-based personalization (simulated)
    const popularTags = document.querySelectorAll('.tag');
    if (popularTags.length > 0) {
        // Simulate location-based tags
        const locationTags = {
            'US': ['STEM Internships', 'Research Opportunities'],
            'EU': ['Extracurricular Activities', 'Career Guidance'],
            'ASIA': ['Tech Opportunities', 'Engineering Programs']
        };
        
        // Default to US tags
        const tags = locationTags['US'];
        popularTags.forEach((tag, index) => {
            if (tags[index]) {
                tag.textContent = tags[index];
            }
        });
    }
}

// Enhanced Micro-Interactions
function addEnhancedMicroInteractions() {
    // Add hover effects for new elements
    const interactiveElements = document.querySelectorAll(
        '.trust-badge, .stat-item, .scarcity-timer, .social-proof-stats'
    );
    
    interactiveElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = 'var(--shadow-lg)';
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    // Add click effects for trust badges
    const trustBadges = document.querySelectorAll('.trust-badge');
    trustBadges.forEach(badge => {
        badge.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

// Track social shares
function trackSocialShare(platform) {
    console.log(`Social share on ${platform}`);
    // Unlock sharing achievement
    if (!localStorage.getItem('shared-platform')) {
        localStorage.setItem('shared-platform', 'true');
        showAchievementBadge({
            id: 'shared-platform',
            name: 'Social Sharer',
            icon: '📱'
        });
    }
    // In a real implementation, this would send analytics data
    // Example: gtag('event', 'social_share', { platform: platform });
}

// Add CSS animations for new elements
function injectAdditionalStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .achievement-badge {
            font-weight: 600;
            font-size: 14px;
        }
        
        .badge-icon {
            font-size: 18px;
        }
    `;
    document.head.appendChild(style);
}

// Initialize additional features
document.addEventListener('DOMContentLoaded', function() {
    addEnhancedMicroInteractions();
    injectAdditionalStyles();
});

// Export for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeSearch,
        handleSearch,
        checkAuthStatus,
        setupMobileMenu,
        shareOnFacebook,
        shareOnTwitter,
        shareOnLinkedIn,
        shareOnWhatsApp,
        initializeScarcityTimer,
        animateStatistics,
        addGamificationElements
    };
}