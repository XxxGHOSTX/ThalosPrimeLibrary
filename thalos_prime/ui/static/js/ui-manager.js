// UI Manager - Handles view switching and UI interactions

class UIManager {
    constructor() {
        this.currentView = 'console';
        this.toastTimeout = 3000;
        this.init();
    }
    
    init() {
        this.setupNavigation();
        this.setupClock();
        this.setupModeSelector();
        this.setupForms();
        this.loadSettings();
        this.updateSessionDisplay();
    }
    
    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-btn');
        navButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const viewName = btn.dataset.view;
                this.switchView(viewName);
                
                // Update active state
                navButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }
    
    switchView(viewName) {
        // Hide all views
        const views = document.querySelectorAll('.view');
        views.forEach(view => view.classList.remove('active'));
        
        // Show target view
        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.classList.add('active');
            this.currentView = viewName;
        }
    }
    
    setupClock() {
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);
    }
    
    updateClock() {
        const clockElement = document.getElementById('utc-clock');
        if (clockElement) {
            const now = new Date();
            const hours = String(now.getUTCHours()).padStart(2, '0');
            const minutes = String(now.getUTCMinutes()).padStart(2, '0');
            const seconds = String(now.getUTCSeconds()).padStart(2, '0');
            clockElement.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }
    
    setupModeSelector() {
        const modeSelector = document.getElementById('search-mode');
        if (modeSelector) {
            // Load saved mode
            const savedMode = localStorage.getItem('search_mode') || 'hybrid';
            modeSelector.value = savedMode;
            
            // Save on change
            modeSelector.addEventListener('change', () => {
                localStorage.setItem('search_mode', modeSelector.value);
                this.showToast('success', 'Mode Updated', `Search mode changed to ${modeSelector.value.toUpperCase()}`);
            });
        }
    }
    
    setupForms() {
        // Search form
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => this.handleSearchSubmit(e));
        }
        
        // Generate form
        const generateForm = document.getElementById('generate-form');
        if (generateForm) {
            generateForm.addEventListener('submit', (e) => this.handleGenerateSubmit(e));
        }
        
        // Enumerate form
        const enumerateForm = document.getElementById('enumerate-form');
        if (enumerateForm) {
            enumerateForm.addEventListener('submit', (e) => this.handleEnumerateSubmit(e));
        }
        
        // Decode form
        const decodeForm = document.getElementById('decode-form');
        if (decodeForm) {
            decodeForm.addEventListener('submit', (e) => this.handleDecodeSubmit(e));
        }
        
        // Settings form
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => this.handleSettingsSubmit(e));
        }
        
        // Reset settings button
        const resetBtn = document.getElementById('reset-settings');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetSettings());
        }
    }
    
    async handleSearchSubmit(e) {
        e.preventDefault();
        this.showLoading();
        
        try {
            const formData = new FormData(e.target);
            const query = formData.get('query');
            const maxResults = parseInt(formData.get('maxResults'));
            const minScore = parseFloat(formData.get('minScore'));
            const mode = document.getElementById('search-mode').value;
            
            const results = await apiClient.search(query, maxResults, mode, minScore);
            this.displaySearchResults(results);
            this.showToast('success', 'Search Complete', `Found ${results.results.length} results`);
        } catch (error) {
            this.showToast('error', 'Search Failed', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async handleGenerateSubmit(e) {
        e.preventDefault();
        this.showLoading();
        
        try {
            const formData = new FormData(e.target);
            const address = formData.get('address') || null;
            const query = formData.get('query') || null;
            const validate = document.getElementById('gen-validate').checked;
            
            const result = await apiClient.generatePage(address, query, validate);
            this.displayGenerateResult(result);
            this.showToast('success', 'Page Generated', 'Page generated successfully');
        } catch (error) {
            this.showToast('error', 'Generation Failed', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async handleEnumerateSubmit(e) {
        e.preventDefault();
        this.showLoading();
        
        try {
            const formData = new FormData(e.target);
            const query = formData.get('query');
            const maxResults = parseInt(formData.get('maxResults'));
            const depth = parseInt(formData.get('depth'));
            
            const results = await apiClient.enumerateAddresses(query, maxResults, depth);
            this.displayEnumerateResults(results);
            this.showToast('success', 'Enumeration Complete', `Found ${results.addresses.length} addresses`);
        } catch (error) {
            this.showToast('error', 'Enumeration Failed', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async handleDecodeSubmit(e) {
        e.preventDefault();
        this.showLoading();
        
        try {
            const formData = new FormData(e.target);
            const address = formData.get('address');
            const text = formData.get('text');
            const query = formData.get('query') || null;
            const normalization = document.getElementById('decode-normalization').value;
            
            const result = await apiClient.decodePage(address, text, query, normalization);
            this.displayDecodeResult(result);
            this.showToast('success', 'Decode Complete', `Coherence score: ${result.coherence.overall_score.toFixed(1)}/100`);
        } catch (error) {
            this.showToast('error', 'Decode Failed', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    handleSettingsSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        // Save settings to localStorage
        for (const [key, value] of formData.entries()) {
            localStorage.setItem(`setting_${key}`, value);
        }
        
        this.showToast('success', 'Settings Saved', 'Your settings have been saved');
        this.applySettings();
    }
    
    loadSettings() {
        // Load theme
        const theme = localStorage.getItem('setting_theme') || 'matrix';
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.value = theme;
        }
        this.applySettings();
    }
    
    applySettings() {
        const theme = localStorage.getItem('setting_theme') || 'matrix';
        document.body.className = `theme-${theme}`;
    }
    
    resetSettings() {
        if (confirm('Reset all settings to default?')) {
            // Clear all settings
            const keys = Object.keys(localStorage).filter(k => k.startsWith('setting_'));
            keys.forEach(key => localStorage.removeItem(key));
            
            this.loadSettings();
            this.showToast('info', 'Settings Reset', 'All settings have been reset to default');
        }
    }
    
    // Display methods
    displaySearchResults(data) {
        const container = document.getElementById('search-results');
        if (!container) return;
        
        container.innerHTML = `
            <div class="results-header">
                <p class="results-count">Found ${data.total_found} results for "${data.query}"</p>
            </div>
            <div class="results-grid">
                ${data.results.map(result => this.renderResultCard(result)).join('')}
            </div>
        `;
    }
    
    renderResultCard(result) {
        const scoreClass = result.coherence.overall_score >= 70 ? 'score-high' : 
                          result.coherence.overall_score >= 40 ? 'score-medium' : 'score-low';
        
        return `
            <div class="result-card">
                <div class="result-header">
                    <span class="result-address">${result.address.hex_address.substring(0, 40)}...</span>
                    <span class="result-score ${scoreClass}">${result.coherence.overall_score.toFixed(1)}/100</span>
                </div>
                <div class="result-content">
                    <p class="result-snippet">${result.snippet}</p>
                </div>
                <div class="result-metadata">
                    <span>Confidence: ${result.coherence.confidence_level}</span>
                    <span>Source: ${result.provenance.source}</span>
                </div>
            </div>
        `;
    }
    
    displayGenerateResult(result) {
        const container = document.getElementById('generate-results');
        if (!container) return;
        
        container.innerHTML = `
            <div class="result-card">
                <div class="result-header">
                    <span class="result-address">Address: ${result.address.hex_address}</span>
                    <span class="result-score ${result.valid ? 'score-high' : 'score-low'}">
                        ${result.valid ? 'Valid' : 'Invalid'}
                    </span>
                </div>
                <div class="result-content">
                    <p><strong>Generation Time:</strong> ${result.generation_time_ms.toFixed(2)}ms</p>
                    <p><strong>Text Preview:</strong></p>
                    <textarea readonly rows="10" style="width: 100%; background: var(--bg-primary); color: var(--matrix-text); border: 1px solid var(--border-dim); padding: 10px; font-family: var(--font-mono);">${result.text}</textarea>
                </div>
            </div>
        `;
    }
    
    displayEnumerateResults(data) {
        const container = document.getElementById('enumerate-results');
        if (!container) return;
        
        container.innerHTML = `
            <div class="results-header">
                <p class="results-count">Found ${data.total_found} addresses for "${data.query}"</p>
            </div>
            <div class="results-grid">
                ${data.addresses.map((addr, idx) => `
                    <div class="result-card">
                        <div class="result-header">
                            <span>${idx + 1}. ${addr.address.substring(0, 40)}...</span>
                            <span class="result-score score-medium">Score: ${addr.score.toFixed(2)}</span>
                        </div>
                        <div class="result-content">
                            <p><strong>N-grams:</strong> ${addr.ngrams.join(', ')}</p>
                            <p><strong>Depth:</strong> ${addr.depth}</p>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    displayDecodeResult(result) {
        const container = document.getElementById('decode-results');
        if (!container) return;
        
        const scoreClass = result.coherence.overall_score >= 70 ? 'score-high' : 
                          result.coherence.overall_score >= 40 ? 'score-medium' : 'score-low';
        
        container.innerHTML = `
            <div class="result-card">
                <div class="result-header">
                    <span class="result-address">Address: ${result.address.hex_address}</span>
                    <span class="result-score ${scoreClass}">${result.coherence.overall_score.toFixed(1)}/100</span>
                </div>
                <div class="result-content">
                    <p><strong>Confidence:</strong> ${result.coherence.confidence_level}</p>
                    <p><strong>Language Score:</strong> ${result.coherence.language_score.toFixed(1)}/100</p>
                    <p><strong>Structure Score:</strong> ${result.coherence.structure_score.toFixed(1)}/100</p>
                    <p><strong>N-gram Score:</strong> ${result.coherence.ngram_score.toFixed(1)}/100</p>
                    <p><strong>Exact Match Score:</strong> ${result.coherence.exact_match_score.toFixed(1)}/100</p>
                    ${result.normalized_text ? `
                        <p><strong>Normalized Text:</strong></p>
                        <textarea readonly rows="5" style="width: 100%; background: var(--bg-primary); color: var(--matrix-text); border: 1px solid var(--border-dim); padding: 10px; font-family: var(--font-mono);">${result.normalized_text}</textarea>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Utility methods
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }
    
    showToast(type, title, message) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${this.getToastIcon(type)}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, this.toastTimeout);
    }
    
    getToastIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }
    
    updateSessionDisplay() {
        const sessionDisplay = document.getElementById('session-id');
        if (sessionDisplay && apiClient) {
            sessionDisplay.textContent = apiClient.sessionId.substring(0, 8) + '...';
        }
    }
}

// Initialize UI Manager
document.addEventListener('DOMContentLoaded', () => {
    window.uiManager = new UIManager();
});
