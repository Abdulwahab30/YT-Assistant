// --- Firebase Config (shared) ---
const firebaseConfig = {
    apiKey: "AIzaSyCeHBMUKXVJzHj_B5JiktrOID7ndR6xYR0",
    authDomain: "yt-assistant-251fb.firebaseapp.com",
    projectId: "yt-assistant-251fb",
    storageBucket: "yt-assistant-251fb.firebasestorage.app",
    messagingSenderId: "35970793550",
    appId: "1:35970793550:web:6d4799707927f462d4831f"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const googleProvider = new firebase.auth.GoogleAuthProvider();

// If already logged in, skip straight to the app
auth.onAuthStateChanged(user => {
    if (user) {
        window.location.href = '/';
    }
});

// --- DOM ---
const loginForm    = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const errorBox     = document.getElementById('auth-error');
const successBox   = document.getElementById('auth-success');

document.getElementById('show-register').addEventListener('click', e => {
    e.preventDefault();
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
    clearMessages();
});

document.getElementById('show-login').addEventListener('click', e => {
    e.preventDefault();
    registerForm.style.display = 'none';
    loginForm.style.display = 'block';
    clearMessages();
});

// --- Helpers ---
function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
    successBox.style.display = 'none';
}
function showSuccess(msg) {
    successBox.textContent = msg;
    successBox.style.display = 'block';
    errorBox.style.display = 'none';
}
function clearMessages() {
    errorBox.style.display = 'none';
    successBox.style.display = 'none';
}
function setLoading(btn, loading) {
    const text   = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');
    btn.disabled = loading;
    text.classList.toggle('hidden', loading);
    loader?.classList.toggle('hidden', !loading);
}
function friendlyError(code) {
    const map = {
        'auth/user-not-found':        'No account found with this email.',
        'auth/wrong-password':        'Incorrect password. Please try again.',
        'auth/invalid-email':         'Please enter a valid email address.',
        'auth/email-already-in-use':  'An account with this email already exists.',
        'auth/weak-password':         'Password must be at least 6 characters.',
        'auth/too-many-requests':     'Too many attempts. Please try again later.',
        'auth/popup-closed-by-user':  'Sign-in popup was closed. Please try again.',
        'auth/cancelled-popup-request': 'Another sign-in is in progress.',
        'auth/network-request-failed': 'Network error. Check your connection.',
    };
    return map[code] || 'Something went wrong. Please try again.';
}

// --- Email Login ---
document.getElementById('email-login-form').addEventListener('submit', async e => {
    e.preventDefault();
    clearMessages();
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn      = document.getElementById('login-btn');

    if (!email || !password) { showError('Please fill in all fields.'); return; }
    setLoading(btn, true);

    try {
        await auth.signInWithEmailAndPassword(email, password);
        // onAuthStateChanged will redirect
    } catch (err) {
        showError(friendlyError(err.code));
        setLoading(btn, false);
    }
});

// --- Email Register ---
document.getElementById('email-register-form').addEventListener('submit', async e => {
    e.preventDefault();
    clearMessages();
    const email    = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const btn      = document.getElementById('register-btn');

    if (!email || !password) { showError('Please fill in all fields.'); return; }
    setLoading(btn, true);

    try {
        await auth.createUserWithEmailAndPassword(email, password);
        // onAuthStateChanged will redirect
    } catch (err) {
        showError(friendlyError(err.code));
        setLoading(btn, false);
    }
});

// --- Google Sign-In (used by both login and register buttons) ---
async function signInWithGoogle() {
    clearMessages();
    try {
        await auth.signInWithPopup(googleProvider);
        // onAuthStateChanged will redirect
    } catch (err) {
        showError(friendlyError(err.code));
    }
}

document.getElementById('google-login-btn').addEventListener('click', signInWithGoogle);
document.getElementById('google-register-btn').addEventListener('click', signInWithGoogle);
