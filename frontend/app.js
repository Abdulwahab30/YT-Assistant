const API_BASE = window.location.origin;
let currentVideoId = null;

// DOM Elements
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

// Icons
const userIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-user"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
const botIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bot"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;

// --- Ingest Video ---
ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = youtubeUrlInput.value.trim();
    if (!url) return;

    // UI Loading State
    ingestBtn.disabled = true;
    ingestBtnText.classList.add('hidden');
    ingestLoader.classList.remove('hidden');
    ingestStatus.className = 'status-msg';
    ingestStatus.textContent = 'Downloading transcript & processing...';
    ingestStatus.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ youtube_url: url })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => null);
            throw new Error(errData?.detail || 'Failed to ingest video');
        }

        const data = await response.json();
        
        // Success
        currentVideoId = data.video_id;
        ingestStatus.textContent = 'Success! Video ingested.';
        ingestStatus.classList.add('success');
        
        // Update Video Info panel
        displayVideoId.textContent = data.video_id;
        displayVideoChunks.textContent = `${data.chunks_created} chunks generated`;
        videoInfo.classList.remove('hidden');

        // Enable Chat
        enableChat();
        
        // Clear chat area if previous session
        chatMessages.innerHTML = '';
        addBotMessage("Video processed successfully! What would you like to know about it?");

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
    if (!currentVideoId) return;

    const question = chatInput.value.trim();
    if (!question) return;

    // Add User Message
    addUserMessage(question);
    chatInput.value = '';
    
    // Disable input while generating
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // Show typing indicator
    const typingIndicatorId = addTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId, question: question })
        });

        if (!response.ok) {
            throw new Error('Failed to get answer');
        }

        const data = await response.json();
        
        // Remove typing indicator
        removeElement(typingIndicatorId);

        // Add Bot Answer
        addBotMessage(data.answer, data.sources);

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
        // Deduplicate sources by text to avoid clutter
        const uniqueSources = [];
        const seen = new Set();
        for (const s of sources) {
            if (!seen.has(s.start)) {
                seen.add(s.start);
                uniqueSources.push(s);
            }
        }
        
        sourcesHTML = '<div class="sources">';
        uniqueSources.forEach(source => {
            sourcesHTML += `
                <a href="${source.youtube_url}" target="_blank" class="source-pill">
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-external-link"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
                    ${source.start} - ${source.end}
                </a>
            `;
        });
        sourcesHTML += '</div>';
    }

    // Format newlines
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
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag])
    );
}
