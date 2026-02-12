// Thalos Prime Chat Application

let sessionId = null;
let lastSeed = null;

// Initialize session
function initSession() {
    // Try to load session from localStorage
    const stored = localStorage.getItem('thalos_session_id');
    if (stored) {
        sessionId = stored;
    } else {
        // Generate new session ID
        sessionId = generateUUID();
        localStorage.setItem('thalos_session_id', sessionId);
    }
    
    updateSessionDisplay();
}

// Generate UUID v4
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Update session ID display
function updateSessionDisplay() {
    const sessionElement = document.getElementById('session-id');
    if (sessionElement && sessionId) {
        sessionElement.textContent = `Session: ${sessionId.substring(0, 8)}...`;
    }
}

// Update seed info display
function updateSeedDisplay(seed) {
    const seedElement = document.getElementById('seed-info');
    if (seedElement && seed !== null) {
        seedElement.textContent = `Last Seed: ${seed}`;
        lastSeed = seed;
    }
}

// Add message to chat
function addMessage(text, isUser, seed = null) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    
    const textDiv = document.createElement('div');
    textDiv.textContent = text;
    messageDiv.appendChild(textDiv);
    
    if (seed !== null && !isUser) {
        const seedTag = document.createElement('div');
        seedTag.className = 'seed-tag';
        seedTag.textContent = `Seed: ${seed}`;
        messageDiv.appendChild(seedTag);
    }
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Send message to API
async function sendMessage(message) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message,
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error sending message:', error);
        throw error;
    }
}

// Handle send button click
async function handleSend() {
    const input = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const message = input.value.trim();
    
    if (!message) {
        return;
    }
    
    // Disable input while processing
    input.disabled = true;
    sendButton.disabled = true;
    
    // Add user message to chat
    addMessage(message, true);
    
    // Clear input
    input.value = '';
    
    try {
        // Send to API
        const response = await sendMessage(message);
        
        // Add bot response
        addMessage(response.response, false, response.seed);
        
        // Update seed display
        updateSeedDisplay(response.seed);
        
    } catch (error) {
        addMessage('Error: Failed to get response. Please try again.', false);
    } finally {
        // Re-enable input
        input.disabled = false;
        sendButton.disabled = false;
        input.focus();
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initSession();
    
    const input = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    
    // Send on button click
    sendButton.addEventListener('click', handleSend);
    
    // Send on Enter key
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSend();
        }
    });
    
    // Focus input
    input.focus();
    
    // Add welcome message
    addMessage('Welcome to Thalos Prime. Ask me anything.', false);
});
