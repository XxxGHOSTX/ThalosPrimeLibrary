// Main Application Entry Point

class ThalosApp {
    constructor() {
        this.version = '1.0.0';
        this.initialized = false;
        
        this.init();
    }
    
    async init() {
        console.log(`%c
╔════════════════════════════════════════════════════════════╗
║                     THALOS PRIME v${this.version}                    ║
║            Symbiotic Intelligence Framework                ║
╚════════════════════════════════════════════════════════════╝
        `, 'color: #00ff41; font-family: monospace;');
        
        try {
            // Fetch API version
            const status = await apiClient.getStatus();
            console.log('API Status:', status);
            
            // Update version display
            const versionElement = document.getElementById('api-version');
            if (versionElement) {
                versionElement.textContent = status.version || this.version;
            }
            
            // Update connection status
            this.updateConnectionStatus('online');
            
            this.initialized = true;
            console.log('Thalos Prime initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize:', error);
            this.updateConnectionStatus('offline');
        }
        
        // Setup global keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Setup periodic health checks
        this.startHealthCheck();
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Focus console input
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const consoleInput = document.getElementById('console-input');
                if (consoleInput) {
                    consoleInput.focus();
                }
            }
            
            // Escape: Clear console input or close modals
            if (e.key === 'Escape') {
                const consoleInput = document.getElementById('console-input');
                if (consoleInput && document.activeElement === consoleInput) {
                    consoleInput.value = '';
                }
            }
            
            // Ctrl/Cmd + /: Show help
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.showHelp();
            }
        });
    }
    
    startHealthCheck() {
        // Check API health every 30 seconds
        setInterval(async () => {
            try {
                await apiClient.getStatus();
                this.updateConnectionStatus('online');
            } catch (error) {
                console.warn('Health check failed:', error);
                this.updateConnectionStatus('offline');
            }
        }, 30000);
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status.toUpperCase();
            statusElement.className = `value status-${status}`;
        }
    }
    
    showHelp() {
        if (window.uiManager) {
            window.uiManager.switchView('docs');
            
            // Update nav
            const navButtons = document.querySelectorAll('.nav-btn');
            navButtons.forEach(btn => {
                btn.classList.toggle('active', btn.dataset.view === 'docs');
            });
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.thalosApp = new ThalosApp();
    
    // Add scan line effect
    const scanline = document.createElement('div');
    scanline.className = 'scanline';
    document.body.appendChild(scanline);
    
    // Expose to console for debugging
    window.Thalos = {
        app: window.thalosApp,
        ui: window.uiManager,
        console: window.consoleHandler,
        api: window.apiClient,
        version: '1.0.0'
    };
    
    console.log('Access Thalos components via window.Thalos');
});

// Handle errors globally
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
