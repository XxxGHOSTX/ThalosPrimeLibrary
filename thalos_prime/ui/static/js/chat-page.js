const MAX_HISTORY_MESSAGES = 20;
const ADDRESS_DISPLAY_LENGTH = 32;

class ChatPage {
    constructor() {
        this.form = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.messages = document.getElementById('messages');
        this.modeSelect = document.getElementById('mode');
        this.minScoreInput = document.getElementById('min-score');
        this.maxResultsInput = document.getElementById('max-results');
        this.sessionId = document.getElementById('session-id');
        this.clearLocalButton = document.getElementById('clear-local');
        this.isSending = false;
        this.init();
    }

    init() {
        if (!this.form || !this.messageInput || !this.messages) return;

        this.sessionId.textContent = apiClient.sessionId;
        this.restoreControlState();

        this.form.addEventListener('submit', (event) => this.handleSubmit(event));
        this.clearLocalButton?.addEventListener('click', () => this.clearLocalView());
        this.modeSelect?.addEventListener('change', () => this.persistControlState());
        this.minScoreInput?.addEventListener('change', () => this.persistControlState());
        this.maxResultsInput?.addEventListener('change', () => this.persistControlState());

        this.addMessage('system', 'Ready. Loading session history...');
        this.loadHistory().catch((error) => {
            this.addMessage('error', `History load failed: ${error.message}`);
        });
    }

    persistControlState() {
        localStorage.setItem('chat_mode', this.modeSelect.value);
        localStorage.setItem('chat_min_score', this.minScoreInput.value);
        localStorage.setItem('chat_max_results', this.maxResultsInput.value);
    }

    restoreControlState() {
        const storedMode = localStorage.getItem('chat_mode');
        const storedMinScore = localStorage.getItem('chat_min_score');
        const storedMaxResults = localStorage.getItem('chat_max_results');
        if (storedMode) this.modeSelect.value = storedMode;
        if (storedMinScore) this.minScoreInput.value = storedMinScore;
        if (storedMaxResults) this.maxResultsInput.value = storedMaxResults;
    }

    async loadHistory() {
        try {
            const history = await apiClient.getChatHistory(MAX_HISTORY_MESSAGES);
            if (!history.history || history.history.length === 0) {
                this.addMessage('system', 'No previous messages in this session.');
                return;
            }

            this.messages.innerHTML = '';
            history.history.forEach((item) => {
                const content = String(item.content || '').trim();
                if (!content) return;
                this.addMessage(item.role || 'system', content, false);
            });
        } catch (error) {
            this.addMessage('error', `History load failed: ${error.message}`);
        }
    }

    async handleSubmit(event) {
        event.preventDefault();
        if (this.isSending) return;

        const text = this.messageInput.value.trim();
        if (!text) return;

        const mode = this.modeSelect.value;
        const minScore = Number(this.minScoreInput.value);
        const maxResults = Number(this.maxResultsInput.value);
        this.persistControlState();
        this.messageInput.value = '';

        this.isSending = true;
        this.addMessage('user', text);
        const typing = this.addMessage('assistant', 'Thinking...', true);

        try {
            const response = await apiClient.sendChat(text, mode, maxResults, minScore);
            typing.remove();
            this.addMessage('assistant', response.reply);
            if (Array.isArray(response.results) && response.results.length > 0) {
                this.addResults(response.results);
            }
        } catch (error) {
            typing.remove();
            this.addMessage('error', error.message);
        } finally {
            this.isSending = false;
        }
    }

    addMessage(role, text, temporary = false) {
        const wrapper = document.createElement('article');
        wrapper.className = `msg ${role === 'error' ? 'error' : ''}`;
        if (temporary) wrapper.dataset.temporary = 'true';

        const roleEl = document.createElement('div');
        roleEl.className = 'msg-role';
        roleEl.textContent = role;

        const textEl = document.createElement('pre');
        textEl.textContent = text;

        wrapper.appendChild(roleEl);
        wrapper.appendChild(textEl);
        this.messages.appendChild(wrapper);
        this.messages.scrollTop = this.messages.scrollHeight;
        return wrapper;
    }

    addResults(results) {
        const wrapper = document.createElement('article');
        wrapper.className = 'msg';

        const roleEl = document.createElement('div');
        roleEl.className = 'msg-role';
        roleEl.textContent = 'results';
        wrapper.appendChild(roleEl);

        const list = document.createElement('div');
        list.className = 'result-list';

        results.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'result';
            const score = Number(result?.coherence?.overall_score ?? 0);
            const address = String(result?.address?.hex_address ?? '');
            const snippet = String(result?.snippet ?? '');
            const displayAddress = address
                ? `${address.slice(0, ADDRESS_DISPLAY_LENGTH)}…`
                : '[none]';
            const displaySnippet = snippet.trim();
            card.textContent = displaySnippet
                ? `#${index + 1} score=${score.toFixed(1)} addr=${displayAddress} ${displaySnippet}`
                : `#${index + 1} score=${score.toFixed(1)} addr=${displayAddress}`;
            list.appendChild(card);
        });

        wrapper.appendChild(list);
        this.messages.appendChild(wrapper);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    clearLocalView() {
        this.messages.innerHTML = '';
        this.addMessage('system', 'Local chat view cleared. Server session history is unchanged.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.chatPage = new ChatPage();
});
