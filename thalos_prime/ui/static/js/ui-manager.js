// UI Manager - Handles view switching and UI interactions

class UIManager {
    constructor() {
        this.currentView = 'console';
        this.toastTimeout = 3000;
        this.serverSettings = null;
        this.draggedView = null;
        this.defaultNavOrder = ['console','search','generate','enumerate','decode','history','settings','docs'];
        this.init();
    }
    
    async init() {
        await this.loadServerSettings();
        this.setupNavigation();
        this.setupClock();
        this.setupModeSelector();
        this.setupForms();
        this.loadSettings();
        this.updateSessionDisplay();
    }
    
    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-btn');
        this.renderTopNav(navButtons);
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

    renderTopNav(navButtons) {
        const topNav = document.getElementById('top-nav');
        if (!topNav) return;
        topNav.innerHTML = '';
        navButtons.forEach((btn) => {
            const clone = btn.cloneNode(true);
            clone.addEventListener('click', () => {
                const viewName = clone.dataset.view;
                this.switchView(viewName);
                document.querySelectorAll('.nav-btn').forEach((b) => {
                    b.classList.toggle('active', b.dataset.view === viewName);
                });
                Array.from(topNav.querySelectorAll('.nav-btn')).forEach((b) => {
                    b.classList.toggle('active', b.dataset.view === viewName);
                });
            });
            topNav.appendChild(clone);
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

        const stopBtn = document.getElementById('stop-server-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', async () => this.handleStopServer());
        }

        const restartBtn = document.getElementById('restart-server-btn');
        if (restartBtn) {
            restartBtn.addEventListener('click', () => window.location.reload());
        }

        this.setupNavOrderDragAndDrop();
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
    
    async handleSettingsSubmit(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        // Save settings to localStorage
        for (const [key, value] of formData.entries()) {
            localStorage.setItem(`setting_${key}`, value);
        }

        const runtimeAutoOpen = document.getElementById('runtime-auto-open')?.checked ?? true;
        const payload = {
            runtime: {
                host: formData.get('runtime_host') || '127.0.0.1',
                port: Number(formData.get('runtime_port') || 8000),
                log_level: formData.get('runtime_log_level') || 'INFO',
                auto_open_browser: runtimeAutoOpen,
            },
            workspace: {
                layout_mode: formData.get('layout_mode') || 'both',
                toolbar_mode: formData.get('toolbar_mode') || 'both',
                nav_order: this.getNavOrder(),
                sidebar_width: Number(formData.get('sidebar_width') || 250),
            },
        };

        try {
            this.serverSettings = await apiClient.updateSettings(payload);
        } catch (error) {
            this.showToast('error', 'Settings Save Failed', error.message);
            return;
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
        this.applyServerSettingsToForm();
        this.renderNavOrder();
        this.applySettings();
    }
    
    applySettings() {
        const theme = localStorage.getItem('setting_theme') || 'matrix';
        const layoutMode = localStorage.getItem('setting_layout_mode') || 'both';
        const toolbarMode = localStorage.getItem('setting_toolbar_mode') || 'both';
        const sidebarWidth = localStorage.getItem('setting_sidebar_width') || '250';
        document.body.className = `theme-${theme} layout-${layoutMode} toolbar-${toolbarMode}`;
        document.body.style.setProperty('--sidebar-width', `${sidebarWidth}px`);
    }
    
    async resetSettings() {
        if (confirm('Reset all settings to default?')) {
            // Clear all settings
            const keys = Object.keys(localStorage).filter(k => k.startsWith('setting_'));
            keys.forEach(key => localStorage.removeItem(key));
            try {
                this.serverSettings = await apiClient.resetSettings();
            } catch (error) {
                this.showToast('error', 'Server Reset Failed', error.message);
            }
            
            this.loadSettings();
            this.showToast('info', 'Settings Reset', 'All settings have been reset to default');
        }
    }

    async loadServerSettings() {
        try {
            this.serverSettings = await apiClient.getSettings();
        } catch (error) {
            this.serverSettings = null;
            console.warn('Failed to load server settings:', error);
        }
    }

    applyServerSettingsToForm() {
        if (!this.serverSettings) return;
        const runtime = this.serverSettings.runtime || {};
        const workspace = this.serverSettings.workspace || {};
        const setValue = (id, value) => {
            const el = document.getElementById(id);
            if (el && value !== undefined && value !== null) el.value = String(value);
        };
        setValue('runtime-host', runtime.host);
        setValue('runtime-port', runtime.port);
        setValue('runtime-log-level', runtime.log_level);
        setValue('layout-mode', workspace.layout_mode);
        setValue('toolbar-mode', workspace.toolbar_mode);
        setValue('sidebar-width', workspace.sidebar_width);
        const autoOpen = document.getElementById('runtime-auto-open');
        if (autoOpen && typeof runtime.auto_open_browser === 'boolean') {
            autoOpen.checked = runtime.auto_open_browser;
        }
        if (Array.isArray(workspace.nav_order)) {
            localStorage.setItem('setting_nav_order', JSON.stringify(workspace.nav_order));
        }
    }

    setupNavOrderDragAndDrop() {
        const list = document.getElementById('nav-order-list');
        if (!list) return;
        list.addEventListener('dragstart', (event) => {
            const target = event.target.closest('.nav-order-item');
            if (!target) return;
            this.draggedView = target.dataset.view;
            target.classList.add('dragging');
        });
        list.addEventListener('dragend', (event) => {
            const target = event.target.closest('.nav-order-item');
            if (!target) return;
            target.classList.remove('dragging');
            this.draggedView = null;
        });
        list.addEventListener('dragover', (event) => {
            event.preventDefault();
            const target = event.target.closest('.nav-order-item');
            if (!target || !this.draggedView || target.dataset.view === this.draggedView) return;
            const dragged = list.querySelector(`[data-view="${this.draggedView}"]`);
            if (!dragged) return;
            const rect = target.getBoundingClientRect();
            const insertAfter = (event.clientY - rect.top) > rect.height / 2;
            if (insertAfter) {
                target.after(dragged);
            } else {
                target.before(dragged);
            }
        });
    }

    renderNavOrder() {
        const list = document.getElementById('nav-order-list');
        if (!list) return;
        const fallback = Array.isArray(this.serverSettings?.workspace?.nav_order)
            ? this.serverSettings.workspace.nav_order
            : this.defaultNavOrder;
        const stored = localStorage.getItem('setting_nav_order');
        let order = fallback;
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                if (Array.isArray(parsed) && parsed.every((item) => typeof item === 'string')) {
                    order = parsed;
                }
            } catch (error) {
                order = fallback;
            }
        }
        list.innerHTML = order.map((view) => `
            <li class="nav-order-item" draggable="true" data-view="${view}">
                ${view.toUpperCase()}
            </li>
        `).join('');
        this.applyNavOrder(order);
    }

    getNavOrder() {
        const list = document.getElementById('nav-order-list');
        if (!list) return this.defaultNavOrder;
        const order = Array.from(list.querySelectorAll('.nav-order-item')).map((el) => el.dataset.view);
        localStorage.setItem('setting_nav_order', JSON.stringify(order));
        this.applyNavOrder(order);
        return order;
    }

    applyNavOrder(order) {
        const navMenu = document.querySelector('.nav-menu');
        const topNav = document.getElementById('top-nav');
        if (!navMenu || !topNav) return;
        order.forEach((view) => {
            const sideBtn = navMenu.querySelector(`.nav-btn[data-view="${view}"]`);
            if (sideBtn) navMenu.appendChild(sideBtn);
        });
        const topButtons = Array.from(topNav.querySelectorAll('.nav-btn'));
        order.forEach((view) => {
            const btn = topButtons.find((b) => b.dataset.view === view);
            if (btn) topNav.appendChild(btn);
        });
    }

    async handleStopServer() {
        try {
            await apiClient.shutdownServer();
            this.showToast('warning', 'Shutdown Requested', 'Server is shutting down');
        } catch (error) {
            this.showToast('error', 'Shutdown Failed', error.message);
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
