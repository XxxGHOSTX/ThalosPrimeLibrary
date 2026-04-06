// Console Handler - Manages the interactive console interface

class ConsoleHandler {
    constructor() {
        this.consoleOutput = document.getElementById('console-output');
        this.consoleInput = document.getElementById('console-input');
        this.sendBtn = document.getElementById('send-btn');
        this.messageHistory = [];
        this.historyIndex = -1;
        this.lastWhyAnswer = null;
        
        this.init();
    }
    
    init() {
        if (!this.consoleInput || !this.sendBtn) return;
        
        // Setup event listeners
        this.sendBtn.addEventListener('click', () => this.handleSend());
        this.consoleInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSend();
            }
        });
        
        // Arrow keys for history
        this.consoleInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory(-1);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory(1);
            }
        });
        
        // Show welcome message
        this.showWelcomeMessage();
        
        // Load history from API
        this.loadHistory();
    }
    
    async handleSend() {
        const message = this.consoleInput.value.trim();
        if (!message) return;
        
        // Add to history
        this.messageHistory.push(message);
        this.historyIndex = this.messageHistory.length;
        
        // Clear input
        this.consoleInput.value = '';
        
        // Display user message
        this.addMessage('user', message);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const mode = document.getElementById('search-mode').value;
            const domain = this.resolveSenseDomain(mode);
            const response = await apiClient.querySense(message, domain, true, true, 0);
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            this.addMessage('bot', response.answer);
            this.renderWhyAnswer(response);
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('error', `Error: ${error.message}`);
        }
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    addMessage(role, content, timestamp = null) {
        if (!this.consoleOutput) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `console-message ${role}`;
        
        const time = timestamp || new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-role ${role}">${role.toUpperCase()}</span>
                <span class="message-timestamp">${time}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        
        this.consoleOutput.appendChild(messageDiv);
    }
    
    addResults(results) {
        if (!this.consoleOutput || !results.length) return;
        
        const resultsDiv = document.createElement('div');
        resultsDiv.className = 'console-message bot';
        
        let resultsHTML = '<div class="message-content"><h4>Search Results:</h4>';
        
        results.forEach((result, index) => {
            const scoreClass = result.coherence.overall_score >= 70 ? 'score-high' : 
                              result.coherence.overall_score >= 40 ? 'score-medium' : 'score-low';
            const provenanceText = `Source: ${result.provenance.source} • Address: ${result.provenance.address}`;
            
            resultsHTML += `
                <div class="result-card">
                    <div class="result-header">
                        <span class="result-address">#${index + 1}: ${result.address.hex_address.substring(0, 30)}...</span>
                        <span class="result-score ${scoreClass}">${result.coherence.overall_score.toFixed(1)}/100</span>
                    </div>
                    <div class="result-content">
                        <p class="result-snippet">${this.escapeHtml(result.snippet)}</p>
                    </div>
                    <div class="result-metadata">
                        <span>Confidence: ${result.coherence.confidence_level}</span>
                        <span>${provenanceText}</span>
                    </div>
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        resultsDiv.innerHTML = resultsHTML;
        
        this.consoleOutput.appendChild(resultsDiv);
    }

    resolveSenseDomain(mode) {
        if (mode === 'local' || mode === 'hybrid') {
            return 'code';
        }
        if (mode === 'remote') {
            return 'knowledge_graph';
        }
        return 'general';
    }

    renderWhyAnswer(response) {
        const panel = document.getElementById('why-answer-panel');
        if (!panel || !response || !response.provenance) return;
        const why = response.provenance.why_this_answer || {};
        const audit = response.provenance.audit_chain || {};
        const epistemics = response.provenance.artifact_epistemics || {};
        const steps = Array.isArray(why.reasoning_steps) ? why.reasoning_steps : [];
        const sources = Array.isArray(response.sources) ? response.sources : [];
        const sourceList = sources.map((source) => `<li>${this.escapeHtml(String(source))}</li>`).join('');
        const stepList = steps.map((step) => `<li>${this.escapeHtml(String(step))}</li>`).join('');

        panel.innerHTML = `
            <div class="message-content">
                <h4>Why this answer</h4>
                <p><strong>Domain:</strong> ${this.escapeHtml(String(response.domain || 'general'))}</p>
                <p><strong>Confidence:</strong> ${Number(response.confidence || 0).toFixed(3)} | <strong>Verified:</strong> ${Boolean(response.verified)}</p>
                <p><strong>Belief state:</strong> ${this.escapeHtml(String(epistemics.belief_state || 'unknown'))}</p>
                <p><strong>Validation:</strong> ${this.escapeHtml(String(epistemics.validation_status || 'unknown'))}</p>
                <p><strong>Artifact ID:</strong> ${this.escapeHtml(String(epistemics.artifact_id || ''))}</p>
                <p><strong>Audit events:</strong> ${this.escapeHtml(String(audit.artifact_event_count || 0))}</p>
                <h5>Sources</h5>
                <ul>${sourceList || '<li>none</li>'}</ul>
                <h5>Reasoning steps</h5>
                <ul>${stepList || '<li>none</li>'}</ul>
            </div>
        `;
        this.lastWhyAnswer = response;
    }
    
    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'console-message bot typing-indicator-message';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="message-header">
                <span class="message-role bot">BOT</span>
            </div>
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        this.consoleOutput.appendChild(indicator);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    showWelcomeMessage() {
        const welcome = `
╔════════════════════════════════════════════════════════════╗
║                     THALOS PRIME v1.0                      ║
║            Symbiotic Intelligence Framework                ║
╚════════════════════════════════════════════════════════════╝

Welcome to Thalos Prime Console

Type your query and press Enter to search the Library of Babel.
Available commands:
  • /help    - Show this help message
  • /clear   - Clear console
  • /history - Show query history
  • /mode    - Change search mode

Ready for input...
        `;
        
        this.addMessage('system', welcome);
    }
    
    async loadHistory() {
        try {
            const history = await apiClient.getChatHistory(10);
            if (history && history.history && history.history.length > 0) {
                this.addMessage('system', `Loaded ${history.history.length} previous messages`);
                
                // Display previous messages
                history.history.forEach(msg => {
                    this.addMessage(msg.role, msg.content, new Date(msg.timestamp * 1000).toLocaleTimeString());
                });
            }
        } catch (error) {
            console.warn('Could not load history:', error);
        }
    }
    
    clearConsole() {
        if (this.consoleOutput) {
            this.consoleOutput.innerHTML = '';
            this.showWelcomeMessage();
        }
    }
    
    navigateHistory(direction) {
        if (this.messageHistory.length === 0) return;
        
        this.historyIndex += direction;
        
        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex >= this.messageHistory.length) {
            this.historyIndex = this.messageHistory.length;
            this.consoleInput.value = '';
            return;
        }
        
        this.consoleInput.value = this.messageHistory[this.historyIndex] || '';
    }
    
    scrollToBottom() {
        if (this.consoleOutput) {
            this.consoleOutput.scrollTop = this.consoleOutput.scrollHeight;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize Console Handler
document.addEventListener('DOMContentLoaded', () => {
    window.consoleHandler = new ConsoleHandler();
});
