const API_BASE = "http://127.0.0.1:8000";
let currentVideoId = null;
let currentUser = null;
let currentSessionId = null;


// --- Firebase Init ---
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

// --- Auth Guard ---
// If user is not logged in, send them to the login page.
// We wait for Firebase to resolve auth state before showing anything.
auth.onAuthStateChanged(user => {
    if (!user) {
        window.location.href = '/login.html';
        return;
    }
    currentUser = user;

    // Populate the header with user info
    const emailEl = document.getElementById('header-user-email');
    const avatarEl = document.getElementById('header-user-avatar');
    if (emailEl) emailEl.textContent = user.email || user.displayName || 'User';
    if (avatarEl && user.photoURL) {
        avatarEl.src = user.photoURL;
        avatarEl.classList.remove('hidden');
    }
    
    loadChatSessions();
});

document.getElementById('signout-btn').addEventListener('click', () => auth.signOut());

// --- DOM Elements ---
const ingestForm = document.getElementById('ingest-form');
const youtubeUrlInput = document.getElementById('youtube-url');
const ingestBtn = document.getElementById('ingest-btn');
const ingestBtnText = ingestBtn.querySelector('.btn-text');
const ingestLoader = ingestBtn.querySelector('.loader');
const ingestStatus = document.getElementById('ingest-status');
const videoInfo = document.getElementById('video-info');
const displayVideoId = document.getElementById('display-video-id');
const displayVideoChunks = document.getElementById('display-video-chunks');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');
const chatSessionsList = document.getElementById('chat-sessions-list');
const newChatBtn = document.getElementById('new-chat-btn');

// --- Icons ---
const userIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
const botIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;

// --- Auth Helper ---
async function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (currentUser) {
        try {
            const token = await currentUser.getIdToken();
            headers['Authorization'] = `Bearer ${token}`;
        } catch (e) {
            console.error("Error getting auth token:", e);
        }
    }
    return headers;
}

// --- Ingest Video ---
ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = youtubeUrlInput.value.trim();
    if (!url) return;

    ingestBtn.disabled = true;
    ingestBtnText.classList.add('hidden');
    ingestLoader.classList.remove('hidden');
    ingestStatus.className = 'status-msg';
    ingestStatus.textContent = 'Downloading transcript & processing...';
    ingestStatus.classList.remove('hidden');

    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/chat/sessions`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ youtube_url: url, force: false })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => null);
            throw new Error(errData?.detail || 'Failed to create session');
        }

        const data = await response.json();

        currentSessionId = data.session.id;
        currentVideoId = data.session.video_id;

        ingestStatus.textContent = 'Success! Session created.';
        ingestStatus.classList.add('success');

        displayVideoId.textContent = data.session.video_title || data.session.video_id;
        displayVideoChunks.textContent = `${data.session.chunks_count} chunks generated`;
        videoInfo.classList.remove('hidden');

        enableChat();
        chatMessages.innerHTML = '';
        addBotMessage("Video processed! What would you like to know about it?");
        
        await loadChatSessions();

    } catch (error) {
        ingestStatus.textContent = error.message;
        ingestStatus.classList.add('error');
    } finally {
        ingestBtn.disabled = false;
        ingestBtnText.classList.remove('hidden');
        ingestLoader.classList.add('hidden');
        youtubeUrlInput.value = '';
    }
});

// --- Chat Logic ---
function enableChat() {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatForm.classList.remove('disabled-form');
    chatInput.focus();
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentSessionId) return;

    const question = chatInput.value.trim();
    if (!question) return;

    addUserMessage(question);
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;

    const typingIndicatorId = addTypingIndicator();

    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ session_id: currentSessionId, question })
        });

        if (!response.ok) throw new Error('Failed to get answer');

        const data = await response.json();
        removeElement(typingIndicatorId);
        addBotMessage(data.answer, data.sources);
        
        await loadChatSessions();

    } catch (error) {
        removeElement(typingIndicatorId);
        addBotMessage("Sorry, I encountered an error while trying to answer your question.");
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
});

// --- UI Helpers ---

function addUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user';
    div.innerHTML = `
        <div class="avatar">${userIcon}</div>
        <div class="message-content">${escapeHTML(text)}</div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addBotMessage(text, sources = []) {
    const div = document.createElement('div');
    div.className = 'message bot';

    let sourcesHTML = '';
    if (sources.length > 0) {
        const uniqueSources = [];
        const seen = new Set();
        for (const s of sources) {
            if (!seen.has(s.start)) { seen.add(s.start); uniqueSources.push(s); }
        }
        sourcesHTML = '<div class="sources">';
        uniqueSources.forEach(source => {
            sourcesHTML += `
                <a href="${source.youtube_url}" target="_blank" class="source-pill">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
                    ${source.start} - ${source.end}
                </a>
            `;
        });
        sourcesHTML += '</div>';
    }

    const formattedText = escapeHTML(text).replace(/\n/g, '<br>');

    div.innerHTML = `
        <div class="avatar">${botIcon}</div>
        <div class="message-content">
            <div>${formattedText}</div>
            ${sourcesHTML}
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.className = 'message bot';
    div.id = id;
    div.innerHTML = `
        <div class="avatar">${botIcon}</div>
        <div class="message-content bot-typing">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
    return id;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag])
    );
}

// --- Session Management ---
async function loadChatSessions() {
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/chat/sessions`, { headers });
        if (!response.ok) return;
        const data = await response.json();
        renderChatSessions(data.sessions || []);
    } catch (e) {
        console.error("Failed to load sessions:", e);
    }
}

function renderChatSessions(sessions) {
    if (!chatSessionsList) return;
    chatSessionsList.innerHTML = '';
    sessions.forEach(session => {
        const li = document.createElement('li');
        li.className = `session-item ${session.id === currentSessionId ? 'active' : ''}`;
        li.style.padding = '10px';
        li.style.borderBottom = '1px solid #333';
        li.style.cursor = 'pointer';
        li.style.color = session.id === currentSessionId ? '#fff' : '#ccc';
        li.style.background = session.id === currentSessionId ? '#333' : 'transparent';
        li.textContent = session.title || 'New Chat';
        li.addEventListener('click', () => selectSession(session));
        chatSessionsList.appendChild(li);
    });
}

async function selectSession(session) {
    if (currentSessionId === session.id && chatMessages.innerHTML !== '') {
        return; // Already active and loaded
    }

    currentSessionId = session.id;
    currentVideoId = session.video_id;
    
    displayVideoId.textContent = session.video_title || session.video_id;
    displayVideoChunks.textContent = `${session.chunks_count} chunks generated`;
    videoInfo.classList.remove('hidden');
    ingestStatus.classList.add('hidden');
    
    chatMessages.innerHTML = '';
    
    await loadChatSessions(); // Re-render to highlight active
    await loadSessionMessages(session.id);

    enableChat();
}

async function loadSessionMessages(sessionId) {
    try {
        const headers = await getAuthHeaders();
        const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`, { headers });
        if (!response.ok) return;
        const data = await response.json();
        
        chatMessages.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                if (msg.role === 'user') {
                    addUserMessage(msg.content);
                } else {
                    addBotMessage(msg.content);
                }
            });
        } else {
            addBotMessage("Video processed! What would you like to know about it?");
        }
    } catch (e) {
        console.error("Failed to load messages:", e);
    }
}

if (newChatBtn) {
    newChatBtn.addEventListener('click', () => {
        currentSessionId = null;
        currentVideoId = null;
        videoInfo.classList.add('hidden');
        chatMessages.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                </div>
                <h3>Ready to Assist</h3>
                <p>Paste a YouTube URL on the left to start chatting about its content.</p>
            </div>
        `;
        chatInput.disabled = true;
        sendBtn.disabled = true;
        chatForm.classList.add('disabled-form');
        ingestStatus.classList.add('hidden');
        youtubeUrlInput.value = '';
        
        loadChatSessions(); // Update active state
    });
}
