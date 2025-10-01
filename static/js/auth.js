// --- static/js/auth.js ---

// Global Firebase variables
let firebaseApp;
let auth;

// Function to initialize Firebase
function initializeFirebase() {
    fetch('/static/firebase_config.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Firebase config not found at /static/firebase_config.json');
            }
            return response.json();
        })
        .then(config => {
            try {
                // Ensure Firebase is not initialized more than once
                if (!firebase.apps.length) {
                    firebaseApp = firebase.initializeApp(config);
                } else {
                    firebaseApp = firebase.app();
                }
                auth = firebase.auth();
                console.log('Firebase initialized successfully.');

                // Set up the listener for authentication state changes
                setupAuthStateObserver();
            } catch (error) {
                console.error('Firebase initialization error:', error);
                updateUIForUnauthenticatedUser(); // Fallback if initialization fails
            }
        })
        .catch(error => {
            console.error('Error loading Firebase config:', error);
            updateUIForUnauthenticatedUser(); // Fallback if config loading fails
        });
}

// Sets up the observer for user sign-in state.
function setupAuthStateObserver() {
    if (!auth) return;

    auth.onAuthStateChanged(user => {
        if (user) {
            // User is signed in.
            console.log('User is signed in:', user.email);
            updateUIForAuthenticatedUser(user);
        } else {
            // User is signed out.
            console.log('User is signed out.');
            updateUIForUnauthenticatedUser();
        }
    });
}

// Updates UI elements for an authenticated user.
function updateUIForAuthenticatedUser(user) {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.innerHTML = `
            <a href="{{ url_for('main.index') }}" class="nav-link">Home</a>
            <a href="{{ url_for('organizations.organizations_page') }}" class="nav-link">Organizations</a>
            <a href="{{ url_for('dashboard.dashboard_page') }}" class="nav-link">Dashboard</a>
            <a href="{{ url_for('profile_page') }}" class="nav-link">Profile</a>
            <a href="#" class="btn btn-secondary" id="logout-btn">Logout</a>
        `;
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }
    }
}

// Updates UI elements for a signed-out user.
function updateUIForUnauthenticatedUser() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.innerHTML = `
            <a href="#features" class="nav-link">Features</a>
            <a href="#how-it-works" class="nav-link">How It Works</a>
            <a href="{{ url_for('login') }}" class="nav-link">Login</a>
            <a href="{{ url_for('signup') }}" class="btn btn-secondary">Sign Up</a>
        `;
    }
}

// Handles the signup form submission.
async function handleSignup(event) {
    event.preventDefault();
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;
    const displayName = form.displayName.value;
    const ageGroup = form.ageGroup.value;

    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, 'Creating Account...');

    try {
        const redirectDestination = sessionStorage.getItem('redirectAfterSignup');
        sessionStorage.removeItem('redirectAfterSignup'); // Clean up

        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, displayName, ageGroup, redirectAfterSignup: redirectDestination })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error.message);

        // Sign in with the custom token from the backend
        await auth.signInWithCustomToken(data.data.customToken);

        // Redirect to the intended page or dashboard
        window.location.href = data.data.redirectAfterSignup || '/dashboard';
    } catch (error) {
        showError('signup-form', error.message);
        setButtonLoading(submitBtn, false, 'Create Account');
    }
}

// Handles the login form submission.
async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const email = form.email.value;
    const password = form.password.value;

    const submitBtn = form.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn, true, 'Signing In...');

    try {
        // Step 1: Sign in with Firebase client SDK to get user and ID token
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        const idToken = await userCredential.user.getIdToken();

        // Step 2: Send ID token to backend to create a server session
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken: idToken })
        });

        if (!response.ok) {
            // If backend fails, sign out from client to prevent inconsistent state
            auth.signOut();
            const data = await response.json();
            throw new Error(data.error.message);
        }

        // Redirect to dashboard on successful server session creation
        window.location.href = '/dashboard';
    } catch (error) {
        showError('login-form', error.message);
        setButtonLoading(submitBtn, false, 'Sign In');
    }
}

// Handles user logout.
function handleLogout(event) {
    event.preventDefault();
    if (auth) {
        auth.signOut()
            .then(() => {
                // After Firebase sign-out, also clear the server session
                fetch('/api/auth/logout', { method: 'POST' })
                    .finally(() => {
                        window.location.href = '/';
                    });
            })
            .catch(error => console.error('Logout error:', error));
    }
}

// ----- Utility Functions -----

// Gets the current authenticated user.
function getCurrentUser() {
    return new Promise((resolve) => {
        if (!auth) {
            const observer = setInterval(() => {
                if (auth) {
                    clearInterval(observer);
                    const unsubscribe = auth.onAuthStateChanged(user => {
                        unsubscribe();
                        resolve(user);
                    });
                }
            }, 50);
        } else {
            const unsubscribe = auth.onAuthStateChanged(user => {
                unsubscribe();
                resolve(user);
            });
        }
    });
}

// Shows an error message within a specific form.
function showError(formId, message) {
    const form = document.getElementById(formId);
    if (form) {
        const errorElement = form.parentElement.querySelector('.error-message');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            setTimeout(() => { errorElement.style.display = 'none'; }, 5000);
        }
    }
}

// Sets the loading state of a button.
function setButtonLoading(button, isLoading, loadingText = 'Loading...') {
    if (!button) return;
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
    }
}


// ----- Main Execution -----

// Initialize Firebase as soon as the script loads.
initializeFirebase();

// Add event listeners once the DOM is fully loaded.
document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signup-form');
    if (signupForm) signupForm.addEventListener('submit', handleSignup);

    const loginForm = document.getElementById('login-form');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);

    // The logout button is added dynamically, so its listener is in updateUIForAuthenticatedUser.
});

// Expose necessary functions globally for other scripts to use
window.authHandlers = {
    getCurrentUser
};