// Firebase Client SDK Authentication Handling
// This file handles client-side authentication with Firebase

// Firebase configuration (will be loaded from firebase_config.json)
const firebaseConfig = {
    // This will be populated from firebase_config.json
};

// Initialize Firebase
let firebaseApp;
let auth;
let db;

try {
    // Load Firebase configuration
    fetch('/static/firebase_config.json')
        .then(response => response.json())
        .then(config => {
            firebaseApp = firebase.initializeApp(config);
            auth = firebaseApp.auth();
            db = firebaseApp.firestore();
            console.log('Firebase initialized successfully');
            
            // Check authentication state
            checkAuthState();
        })
        .catch(error => {
            console.error('Error loading Firebase config:', error);
        });
} catch (error) {
    console.error('Firebase initialization error:', error);
}

// Check authentication state
function checkAuthState() {
    if (!auth) return;
    
    auth.onAuthStateChanged((user) => {
        if (user) {
            // User is signed in
            console.log('User signed in:', user.email);
            updateUIForAuthenticatedUser(user);
        } else {
            // User is signed out
            console.log('User signed out');
            updateUIForUnauthenticatedUser();
        }
    });
}

// Update UI for authenticated user
function updateUIForAuthenticatedUser(user) {
    // Update navigation
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.innerHTML = `
            <a href="#features" class="nav-link">Features</a>
            <a href="#how-it-works" class="nav-link">How It Works</a>
            <a href="/profile" class="nav-link">Profile</a>
            <a href="#" class="btn btn-secondary" id="logout-btn">Logout</a>
        `;
        document.getElementById('logout-btn').addEventListener('click', handleLogout);
    }
    
    // Update landing page CTA buttons
    const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
    if (aiAnalysisBtn) {
        aiAnalysisBtn.textContent = '🤖 Start AI Analysis';
        aiAnalysisBtn.href = '/ai-analysis'; // This would be your AI analysis page
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
    
    // Update landing page CTA buttons
    const aiAnalysisBtn = document.getElementById('ai-analysis-btn');
    if (aiAnalysisBtn) {
        aiAnalysisBtn.textContent = '🤖 Get AI Analysis';
        aiAnalysisBtn.href = '/signup'; // Redirect to signup
    }
}

// Handle signup form submission
function handleSignup(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;
    const displayName = form.displayName.value;
    const ageGroup = form.ageGroup.value;
    
    const errorMessage = document.getElementById('error-message');
    const successMessage = document.getElementById('success-message');
    
    // Basic validation
    if (!email || !password || !displayName || !ageGroup) {
        showError(errorMessage, 'Please fill in all fields');
        return;
    }
    
    if (password.length < 6) {
        showError(errorMessage, 'Password must be at least 6 characters');
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating account...';
    submitBtn.disabled = true;
    
    // Send signup request to backend
    fetch('/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            email,
            password,
            displayName,
            ageGroup
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Sign in with custom token
            return auth.signInWithCustomToken(data.data.customToken);
        } else {
            throw new Error(data.error.message);
        }
    })
    .then(() => {
        showSuccess(successMessage, 'Account created successfully! Redirecting...');
        setTimeout(() => {
            window.location.href = '/profile';
        }, 2000);
    })
    .catch(error => {
        showError(errorMessage, error.message);
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    });
}

// Handle login form submission
function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;
    
    const errorMessage = document.getElementById('error-message');
    const successMessage = document.getElementById('success-message');
    
    if (!email || !password) {
        showError(errorMessage, 'Please fill in all fields');
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;
    
    // Sign in with Firebase Auth
    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            showSuccess(successMessage, 'Login successful! Redirecting...');
            setTimeout(() => {
                window.location.href = '/profile';
            }, 2000);
        })
        .catch((error) => {
            showError(errorMessage, getFirebaseErrorMessage(error));
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        });
}

// Handle logout
function handleLogout(event) {
    event.preventDefault();
    
    auth.signOut()
        .then(() => {
            console.log('User signed out');
            window.location.href = '/';
        })
        .catch((error) => {
            console.error('Logout error:', error);
        });
}

// Utility functions
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

function showSuccess(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

function getFirebaseErrorMessage(error) {
    switch (error.code) {
        case 'auth/invalid-email':
            return 'Invalid email address';
        case 'auth/user-disabled':
            return 'User account is disabled';
        case 'auth/user-not-found':
            return 'No user found with this email';
        case 'auth/wrong-password':
            return 'Incorrect password';
        case 'auth/too-many-requests':
            return 'Too many attempts. Please try again later';
        default:
            return 'Authentication failed. Please try again';
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Signup form
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }
    
    // Login form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Logout button (if exists on page load)
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Logout link in profile
    const logoutLink = document.getElementById('logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', handleLogout);
    }
    
    // Check if we need to redirect authenticated users
    if (auth && window.location.pathname === '/signup') {
        auth.onAuthStateChanged((user) => {
            if (user) {
                window.location.href = '/profile';
            }
        });
    }
    
    if (auth && window.location.pathname === '/login') {
        auth.onAuthStateChanged((user) => {
            if (user) {
                window.location.href = '/profile';
            }
        });
    }
});

// Check AI analysis limits
async function checkAIAnalysisLimit() {
    try {
        const user = await getCurrentUser();
        if (!user) {
            return { hasAccess: false, plan: 'free', remaining: 0 };
        }

        const response = await fetch(`/api/auth/check-ai-limit?uid=${user.uid}`);
        const data = await response.json();
        
        if (data.success) {
            return data.data;
        } else {
            console.error('Error checking AI limit:', data.error);
            return { hasAccess: false, plan: 'free', remaining: 0 };
        }
    } catch (error) {
        console.error('Error checking AI analysis limit:', error);
        return { hasAccess: false, plan: 'free', remaining: 0 };
    }
}

// Get current authenticated user
async function getCurrentUser() {
    return new Promise((resolve) => {
        if (!auth) {
            resolve(null);
            return;
        }
        
        const user = auth.currentUser;
        if (user) {
            resolve(user);
        } else {
            // Wait for auth state to be determined
            const unsubscribe = auth.onAuthStateChanged((user) => {
                unsubscribe();
                resolve(user);
            });
        }
    });
}

// Export for use in other files
window.authHandlers = {
    checkAuthState,
    handleSignup,
    handleLogin,
    handleLogout,
    checkAIAnalysisLimit,
    getCurrentUser
};