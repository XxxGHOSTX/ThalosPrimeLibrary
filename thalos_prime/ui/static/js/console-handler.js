// Console Handler - Manages the interactive console interface

class ConsoleHandler {
    constructor() {
        this.consoleOutput = document.getElementById('console-output');
        this.consoleInput = document.getElementById('console-input');
        this.sendBtn = document.getElementById('send-btn');
        this.messageHistory = [];
        this.historyIndex = -1;
        
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

        if (message.startsWith('/benchmark-tasks')) {
            this.messageHistory.push(message);
            this.historyIndex = this.messageHistory.length;
            this.consoleInput.value = '';
            this.addMessage('user', message);
            this.showTypingIndicator();
            try {
                const tasks = await apiClient.getBenchmarkTasks();
                this.hideTypingIndicator();
                const lines = tasks.tasks.map((t) => `${t.task_id}: ${t.title}`);
                this.addMessage('bot', `Available benchmark tasks (${tasks.count}):\n${lines.join('\n')}`);
            } catch (error) {
                this.hideTypingIndicator();
                this.addMessage('error', `Error: ${error.message}`);
            }
            this.scrollToBottom();
            return;
        }

        if (message.startsWith('/benchmark')) {
            this.messageHistory.push(message);
            this.historyIndex = this.messageHistory.length;
            this.consoleInput.value = '';
            this.addMessage('user', message);
            this.showTypingIndicator();

            const tokens = message.split(/\s+/).filter(Boolean);
            const taskId = tokens[1] || 'latent-11';
            const seed = Number.parseInt(tokens[2] || '2026', 10);
            const perturbation = Number.parseInt(tokens[3] || '0', 10);

            try {
                const result = await apiClient.runBenchmark(taskId, seed, perturbation);
                this.hideTypingIndicator();
                const summary = [
                    `Benchmark: ${result.benchmark}`,
                    `Task: ${result.task_id}`,
                    `Seed: ${result.seed}  Perturbation: ${result.perturbation}`,
                    `Selected Candidate: ${result.selected_candidate}`,
                    `Selected Address: ${result.selected_address}`,
                    `Constraints Pass: ${result.constraints_pass}`,
                    `Stabilized: ${result.stabilized}`,
                    `Query: ${result.selected_query}`,
                ].join('\n');
                this.addMessage('bot', summary);
            } catch (error) {
                this.hideTypingIndicator();
                this.addMessage('error', `Error: ${error.message}`);
            }
            this.scrollToBottom();
            return;
        }

        if (message.startsWith('/benchmark-compare')) {
            this.messageHistory.push(message);
            this.historyIndex = this.messageHistory.length;
            this.consoleInput.value = '';
            this.addMessage('user', message);
            this.showTypingIndicator();

            const tokens = message.split(/\s+/).filter(Boolean);
            const seed = Number.parseInt(tokens[1] || '2026', 10);
            const perturbation = Number.parseInt(tokens[2] || '0', 10);

            try {
                const result = await apiClient.compareBenchmark(seed, perturbation);
                this.hideTypingIndicator();
                const summary = result.summary;
                const lines = [
                    `Benchmark: ${result.benchmark}`,
                    `Tasks: ${result.task_count}`,
                    `Operational Mean: ${summary.operational_mean_score.toFixed(6)}`,
                    `Noisy Baseline Mean: ${summary.noisy_baseline_mean_score.toFixed(6)}`,
                    `Random Baseline Mean: ${summary.random_baseline_mean_score.toFixed(6)}`,
                    `Win Rate vs Noisy: ${(summary.operational_vs_noisy_win_rate * 100).toFixed(2)}%`,
                    `Win Rate vs Random: ${(summary.operational_vs_random_win_rate * 100).toFixed(2)}%`,
                    `Outperforms Both Means: ${summary.operational_outperforms_both_means}`,
                ];
                this.addMessage('bot', lines.join('\n'));
            } catch (error) {
                this.hideTypingIndicator();
                this.addMessage('error', `Error: ${error.message}`);
            }
            this.scrollToBottom();
            return;
        }
        
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
            // Get search mode
            const mode = document.getElementById('search-mode').value;
            
            // Send to API
            const response = await apiClient.sendChat(message, mode, 5, 51);
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            // Display bot response
            this.addMessage('bot', response.reply);
            
            // Display results if any
            if (response.results && response.results.length > 0) {
                this.addResults(response.results);
            }
            
            // Show metadata
            if (response.metadata && response.metadata.query_time_ms) {
                const timeMsg = `Query processed in ${response.metadata.query_time_ms.toFixed(0)}ms`;
                this.addMessage('system', timeMsg);
            }
            if (response.metadata && Object.prototype.hasOwnProperty.call(response.metadata, 'high_coherence_satisfied')) {
                const satisfied = Boolean(response.metadata.high_coherence_satisfied);
                const attempts = response.metadata.attempts ?? 1;
                const minScore = response.metadata.min_score_target ?? 51;
                const statusText = satisfied
                    ? `High coherence satisfied (≥${minScore}) in ${attempts} attempt(s).`
                    : `High coherence fallback used (target ≥${minScore}) after ${attempts} attempt(s).`;
                this.addMessage(satisfied ? 'system' : 'error', statusText);
            }
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
    • /benchmark-tasks - List benchmark tasks
    • /benchmark <task_id> <seed> <perturbation> - Run benchmark
    • /benchmark-compare <seed> <perturbation> - Compare against baselines

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
