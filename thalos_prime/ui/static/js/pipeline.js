// Pipeline View — Full end-to-end query → enumerate → generate → score → synthesize
// All advanced capabilities are always-on: adaptive search, coherence amplification,
// diversity reranking, query expansion, and coherence floor enforcement are automatic.

'use strict';

class PipelineRunner {
    constructor() {
        this._stages = ['query', 'enumerate', 'generate', 'score', 'synthesize'];
        this._form = document.getElementById('pipeline-form');
        this._stagesEl = document.getElementById('pipeline-stages');
        this._resultsEl = document.getElementById('pipeline-results');
        this._enumOutput = document.getElementById('pipeline-enum-output');
        this._pagesOutput = document.getElementById('pipeline-pages-output');
        this._synthOutput = document.getElementById('pipeline-synth-output');

        if (this._form) {
            this._form.addEventListener('submit', (e) => {
                e.preventDefault();
                this._run();
            });
        }
    }

    _setStageStatus(stage, status) {
        const el = document.getElementById(`stage-${stage}-status`);
        const node = document.getElementById(`stage-${stage}`);
        if (!el || !node) return;
        el.textContent = status;
        node.className = 'stage-node';
        if (status === 'RUNNING') node.classList.add('stage-running');
        else if (status === 'DONE') node.classList.add('stage-done');
        else if (status === 'ERROR') node.classList.add('stage-error');
        else node.classList.add('stage-pending');
    }

    _resetStages() {
        this._stages.forEach(s => this._setStageStatus(s, 'PENDING'));
        this._stagesEl.classList.remove('hidden');
        this._resultsEl.classList.add('hidden');
        if (this._enumOutput) this._enumOutput.innerHTML = '';
        if (this._pagesOutput) this._pagesOutput.innerHTML = '';
        if (this._synthOutput) this._synthOutput.innerHTML = '';
    }

    async _run() {
        const query = (document.getElementById('pipeline-query') || {}).value || '';
        const maxResults = parseInt((document.getElementById('pipeline-max-results') || {}).value || '5', 10);
        const depth = parseInt((document.getElementById('pipeline-depth') || {}).value || '2', 10);

        if (!query.trim()) return;

        this._resetStages();

        // Stage 1: Query normalisation
        this._setStageStatus('query', 'RUNNING');
        await this._delay(120);
        this._setStageStatus('query', 'DONE');

        // Stage 2: Enumerate addresses — POST to /api/v1/enumerate with JSON body
        this._setStageStatus('enumerate', 'RUNNING');
        let addresses = [];
        try {
            const enumRes = await fetch('/api/v1/enumerate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, max_results: maxResults, depth }),
            });
            if (enumRes.ok) {
                const enumData = await enumRes.json();
                addresses = enumData.addresses || enumData.results || [];
            }
        } catch (_) { /* network unavailable in offline/test mode */ }
        this._renderEnum(addresses, query);
        this._setStageStatus('enumerate', 'DONE');

        // Stage 3+4: Generate pages and score via adaptive search (always-on)
        this._setStageStatus('generate', 'RUNNING');
        this._setStageStatus('score', 'RUNNING');
        let searchResults = [];
        try {
            const searchRes = await fetch('/api/v1/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    max_results: maxResults,
                    // All optimizations are always-on by default:
                    enable_adaptive_optimization: true,
                    enable_query_expansion: true,
                    enable_diversity_rerank: true,
                }),
            });
            if (searchRes.ok) {
                const searchData = await searchRes.json();
                searchResults = searchData.results || [];
            }
        } catch (_) { /* offline mode */ }
        this._renderPages(searchResults);
        this._setStageStatus('generate', 'DONE');
        this._setStageStatus('score', 'DONE');

        // Stage 5: Synthesize
        this._setStageStatus('synthesize', 'RUNNING');
        let synthResult = null;
        try {
            const synthRes = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: query, session_id: null }),
            });
            if (synthRes.ok) {
                synthResult = await synthRes.json();
            }
        } catch (_) { /* offline mode */ }
        this._renderSynth(synthResult, query, searchResults);
        this._setStageStatus('synthesize', 'DONE');

        this._resultsEl.classList.remove('hidden');
    }

    _renderEnum(addresses, query) {
        if (!this._enumOutput) return;
        if (!addresses.length) {
            this._enumOutput.innerHTML = '<span class="dim-text">No addresses returned (offline or API unavailable)</span>';
            return;
        }
        const rows = addresses.slice(0, 10).map((a, i) => {
            const rawAddr = typeof a === 'string' ? a : (a.address || JSON.stringify(a));
            const addr = this._escHtml(rawAddr);
            const rawScore = typeof a === 'object' && a.score != null ? Number(a.score).toFixed(3) : null;
            const score = rawScore != null ? ` <span class="score-badge">${this._escHtml(rawScore)}</span>` : '';
            return `<div class="enum-row"><span class="enum-idx">${String(i + 1).padStart(2, '0')}</span> <span class="enum-addr">${addr}</span>${score}</div>`;
        });
        this._enumOutput.innerHTML = rows.join('');
    }

    _renderPages(results) {
        if (!this._pagesOutput) return;
        if (!results.length) {
            this._pagesOutput.innerHTML = '<span class="dim-text">No pages returned (offline or API unavailable)</span>';
            return;
        }
        const cards = results.slice(0, 5).map(r => {
            const score = r.coherence ? r.coherence.overall_score : (r.score || 0);
            // r.address is an AddressInfo object {hex_address, url, ...}; extract string.
            const rawAddr = (r.address && (r.address.hex_address || r.address.url)) || r.id || '—';
            const text = r.page_text || r.text || '';
            const rawPreview = text.length > 200 ? text.slice(0, 200) + '…' : text;
            const addr = this._escHtml(rawAddr);
            const preview = this._escHtml(rawPreview);
            const scoreClass = score >= 90 ? 'score-high' : score >= 79 ? 'score-mid' : 'score-low';
            return `
                <div class="page-card">
                    <div class="page-card-header">
                        <span class="page-addr">${addr}</span>
                        <span class="page-score ${scoreClass}">${this._escHtml(Number(score).toFixed(1))}/100</span>
                    </div>
                    <div class="page-preview">${preview}</div>
                </div>`;
        });
        this._pagesOutput.innerHTML = cards.join('');
    }

    /** Escape a string for safe insertion as HTML text content. */
    _escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    _renderSynth(result, query, pages) {
        if (!this._synthOutput) return;
        const safeQuery = this._escHtml(query);
        if (!result) {
            // Offline fallback: summarise from pages
            const best = pages[0];
            const score = best && best.coherence ? best.coherence.overall_score.toFixed(1) : '—';
            const safeScore = this._escHtml(score);
            this._synthOutput.innerHTML = `
                <div class="synth-card">
                    <div class="synth-query">&gt; Query: <em>${safeQuery}</em></div>
                    <div class="synth-note">Best coherence score: <strong>${safeScore}/100</strong></div>
                    <div class="synth-note dim-text">(API unavailable — synthesis from local results)</div>
                </div>`;
            return;
        }
        // ChatResponse has the assistant reply in `reply`; fall back for other shapes.
        const resp = result.reply || result.response || result.message || result.text || JSON.stringify(result);
        const safeResp = this._escHtml(resp);
        this._synthOutput.innerHTML = `
            <div class="synth-card">
                <div class="synth-query">&gt; Query: <em>${safeQuery}</em></div>
                <div class="synth-response">${safeResp}</div>
            </div>`;
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.pipelineRunner = new PipelineRunner();
});
