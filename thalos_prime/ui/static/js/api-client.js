// API Client - Handles all API communications

// Supported search/chat modes.
const SEARCH_MODES = Object.freeze({
    LOCAL: 'local',
    REMOTE: 'remote',
    HYBRID: 'hybrid',
    GENERATIVE: 'generative',
});

class APIClient {
    constructor(baseURL = '/api/v1') {
        this.baseURL = baseURL;
        this.sessionId = this.loadSessionId();
        // Expose mode constants on the instance for UI convenience.
        this.MODES = SEARCH_MODES;
    }
    
    loadSessionId() {
        let sessionId = localStorage.getItem('thalos_session_id');
        if (!sessionId) {
            sessionId = this.generateUUID();
            localStorage.setItem('thalos_session_id', sessionId);
        }
        return sessionId;
    }
    
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, mergedOptions);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    // Chat endpoints
    // Default mode is 'generative' for coherent responses; default min_score is 80.
    async sendChat(message, mode = SEARCH_MODES.GENERATIVE, maxResults = 5, minScore = 80) {
        return this.request(`/chat`, {
            method: 'POST',
            body: JSON.stringify({
                message,
                session_id: this.sessionId,
                max_results: maxResults,
                mode,
                min_score: minScore,
            })
        });
    }
    
    async getChatHistory(limit = 20) {
        return this.request(`/chat/history/${this.sessionId}?limit=${limit}`);
    }
    
    // Search endpoints
    async search(query, maxResults = 10, mode = SEARCH_MODES.HYBRID, minScore = 0) {
        return this.request('/search/', {
            method: 'POST',
            body: JSON.stringify({
                query,
                max_results: maxResults,
                mode,
                min_score: minScore
            })
        });
    }
    
    async getSearchSuggestions(query) {
        return this.request(`/search/suggestions?q=${encodeURIComponent(query)}`);
    }
    
    async clearSearchCache() {
        return this.request('/search/cache', {
            method: 'DELETE'
        });
    }
    
    // Generate endpoints
    async generatePage(address = null, query = null, validate = true) {
        return this.request('/generate/', {
            method: 'POST',
            body: JSON.stringify({
                address,
                query,
                validate
            })
        });
    }
    
    async generateRandom(seed = null) {
        const url = seed ? `/generate/random?seed=${encodeURIComponent(seed)}` : '/generate/random';
        return this.request(url);
    }
    
    async validatePage(address, text) {
        return this.request('/generate/validate', {
            method: 'POST',
            body: JSON.stringify({
                address,
                text
            })
        });
    }
    
    // Enumerate endpoints
    async enumerateAddresses(query, maxResults = 10, depth = 2) {
        return this.request('/enumerate/', {
            method: 'POST',
            body: JSON.stringify({
                query,
                max_results: maxResults,
                depth
            })
        });
    }
    
    async extractNgrams(text, minSize = 2, maxSize = 5) {
        return this.request('/enumerate/ngrams', {
            method: 'POST',
            body: JSON.stringify({
                text,
                min_size: minSize,
                max_size: maxSize
            })
        });
    }
    
    // Decode endpoints
    async decodePage(address, text, query = null, normalization = 'heuristic') {
        return this.request('/decode/', {
            method: 'POST',
            body: JSON.stringify({
                address,
                text,
                query,
                normalization
            })
        });
    }
    
    async scoreText(text, query = null) {
        return this.request('/decode/score', {
            method: 'POST',
            body: JSON.stringify({
                text,
                query
            })
        });
    }
    
    // Status endpoints
    async getStatus() {
        return this.request('/status', { method: 'GET' });
    }
    
    async getVersion() {
        const status = await this.getStatus();
        return status.version;
    }
}

// Export singleton instance
const apiClient = new APIClient();
window.apiClient = apiClient;
