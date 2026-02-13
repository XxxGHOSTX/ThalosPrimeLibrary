from typing import Any
from functools import wraps

API_TITLE = "Thalos Prime API"

try:

    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    FASTAPI_AVAILABLE = True

except ModuleNotFoundError:

    FASTAPI_AVAILABLE = False

    class _UnavailableFastAPI:

        def __init__(self, *args: Any, **kwargs: Any) -> None:

            self.title = API_TITLE

        def get(self, *args: Any, **kwargs: Any):

            return self._decorate

        def post(self, *args: Any, **kwargs: Any):

            return self._decorate

        def put(self, *args: Any, **kwargs: Any):

            return self._decorate

        def delete(self, *args: Any, **kwargs: Any):

            return self._decorate

        def patch(self, *args: Any, **kwargs: Any):

            return self._decorate

        def head(self, *args: Any, **kwargs: Any):

            return self._decorate

        def options(self, *args: Any, **kwargs: Any):

            return self._decorate

        def _decorate(self, func):

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:

                raise RuntimeError("FastAPI dependency not installed")

            return wrapper

    class _UnavailableRequest:

        """Placeholder request type used when FastAPI is not installed.

        Using this stub in place of the real Request will typically fail at runtime,
        mirroring the explicit RuntimeError raised by the placeholder FastAPI decorator.
        """

    class _UnavailableResponse(dict):

        def __init__(self, *args: Any, **kwargs: Any) -> None:

            super().__init__(*args, **kwargs)

    FastAPI = _UnavailableFastAPI  # type: ignore[assignment]

    Request = _UnavailableRequest

    HTMLResponse = _UnavailableResponse  # type: ignore

    JSONResponse = _UnavailableResponse  # type: ignore

from datetime import datetime

import uuid

import time



app = FastAPI(title=API_TITLE)



# Define COMMON_WORDS before any function that uses it

COMMON_WORDS = {

    "the", "and", "of", "to", "in", "is", "that", "it", "you", "a", "for", "on",

    "with", "as", "are", "this", "be", "or", "by", "from", "an", "at", "not"

}



# Cache for search results

_SEARCH_CACHE = {}

_CACHE_TIMEOUT = 3600



MATRIX_HTML = """<!DOCTYPE html>

<html lang=\"en\">

<head>

  <meta charset=\"UTF-8\" />

  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />

  <title>Thalos Prime Matrix Console</title>

  <style>

    html, body { height: 100%; margin: 0; background: #020202; color: #00ff88; font-family: monospace; overflow: hidden; }

    #matrix { position: fixed; inset: 0; z-index: 1; opacity: 0.25; }

    #splash { position: fixed; inset: 0; z-index: 3; background: radial-gradient(ellipse at center, rgba(0,40,0,0.35), rgba(0,0,0,0.95)); }

    #overlay { position: relative; z-index: 2; height: 100%; display: none; flex-direction: column; backdrop-filter: blur(1px); }

    header { padding: 12px 16px; border-bottom: 1px solid rgba(0,255,136,0.2); display: flex; justify-content: space-between; background: rgba(0,0,0,0.55); }

    #chat { flex: 1; overflow-y: auto; padding: 16px; background: rgba(0,0,0,0.45); }

    .msg { margin-bottom: 12px; white-space: pre-wrap; }

    .user { color: #9effc5; }

    .bot { color: #00ff88; }

    .meta { color: #00aa66; font-size: 12px; }

    #inputbar { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid rgba(0,255,136,0.2); background: rgba(0,0,0,0.55); }

    #prompt { flex: 1; background: #0b0b0b; color: #00ff88; border: 1px solid rgba(0,255,136,0.3); padding: 10px; }

    #send { background: #00ff88; color: #031a10; border: none; padding: 10px 14px; font-weight: bold; cursor: pointer; }

    #splash-ui { position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 32px; }

    #enter { background: rgba(0,255,136,0.2); border: 1px solid rgba(0,255,136,0.5); color: #00ff88; padding: 10px 16px; cursor: pointer; font-weight: bold; }

  </style>

</head>

<body>

  <canvas id=\"matrix\"></canvas>

  <canvas id=\"splash\"></canvas>

  <div id=\"splash-ui\">

    <button id=\"enter\">ENTER THE MATRIX</button>

  </div>

  <div id=\"overlay\">

    <header>

      <div>Thalos Prime :: Matrix Console</div>

      <div id=\"clock\" class=\"meta\">--:--:-- UTC</div>

    </header>

    <div id=\"chat\"></div>

    <div id=\"inputbar\">

      <input id=\"prompt\" type=\"text\" placeholder=\"Type a command or message...\" />

      <button id=\"send\">Send</button>

    </div>

  </div>

  <script>

    const chat = document.getElementById('chat');

    const promptEl = document.getElementById('prompt');

    const sendBtn = document.getElementById('send');

    const clockEl = document.getElementById('clock');

    const sessionKey = 'tp_session_id';

    const splashCanvas = document.getElementById('splash');

    const matrixCanvas = document.getElementById('matrix');

    const overlay = document.getElementById('overlay');

    const enterBtn = document.getElementById('enter');



    function updateClock() {

      const now = new Date();

      clockEl.textContent = now.toISOString().split('T')[1].split('.')[0] + ' UTC';

    }



    function addMessage(role, text) {

      const div = document.createElement('div');

      div.className = 'msg ' + role;

      div.textContent = text;

      chat.appendChild(div);

      chat.scrollTop = chat.scrollHeight;

    }



    async function sendMessage() {

      const message = promptEl.value.trim();

      if (!message) return;

      addMessage('user', '> ' + message);

      promptEl.value = '';



      let sessionId = localStorage.getItem(sessionKey);

      const payload = { message, session_id: sessionId };



      try {

        const res = await fetch('/chat', {

          method: 'POST',

          headers: { 'Content-Type': 'application/json' },

          body: JSON.stringify(payload)

        });

        const data = await res.json();

        if (data.session_id) localStorage.setItem(sessionKey, data.session_id);

        addMessage('bot', data.reply || '[No reply]');

      } catch (err) {

        addMessage('bot', 'ERROR: Unable to reach core.');

      }

    }



    sendBtn.addEventListener('click', sendMessage);

    promptEl.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });



    function matrixRain() {

      const ctx = matrixCanvas.getContext('2d');

      const resize = () => {

        matrixCanvas.width = window.innerWidth;

        matrixCanvas.height = window.innerHeight;

      };

      window.addEventListener('resize', resize);

      resize();



      const letters = '01ABCDEFGHIJKLMNOPQRSTUVWXYZ@$%#*';

      const fontSize = 11;

      let columns = Math.floor(matrixCanvas.width / fontSize);

      let drops = Array(columns).fill(1);



      setInterval(() => {

        ctx.fillStyle = 'rgba(2, 8, 4, 0.10)';

        ctx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);

        ctx.fillStyle = 'rgba(0, 255, 136, 0.65)';

        ctx.font = fontSize + 'px monospace';



        columns = Math.floor(matrixCanvas.width / fontSize);

        if (drops.length !== columns) drops = Array(columns).fill(1);



        for (let i = 0; i < drops.length; i++) {

          const text = letters.charAt(Math.floor(Math.random() * letters.length));

          ctx.fillText(text, i * fontSize, drops[i] * fontSize);

          if (drops[i] * fontSize > matrixCanvas.height && Math.random() > 0.985) drops[i] = 0;

          drops[i] += 0.6; // slower fall

        }

      }, 80);

    }



    function splashScene() {

      const ctx = splashCanvas.getContext('2d');

      const W = () => window.innerWidth;

      const H = () => window.innerHeight;

      const agents = Array.from({ length: 6 }).map((_, i) => ({ x: Math.random() * W(), y: H() - 120 - Math.random() * 60, speed: 3 + Math.random() * 2, dir: i % 2 === 0 ? 1 : -1 }));

      const rain = Array.from({ length: 200 }).map(() => ({ x: Math.random() * W(), y: Math.random() * H(), speed: 6 + Math.random() * 4 }));

      const neo = { x: W() * 0.55, y: H() - 140, sway: 0 };



      const resize = () => {

        splashCanvas.width = W();

        splashCanvas.height = H();

      };

      window.addEventListener('resize', resize);

      resize();



      function drawCity() {

        ctx.fillStyle = '#010101';

        ctx.fillRect(0, 0, splashCanvas.width, splashCanvas.height);

        ctx.fillStyle = '#040a0a';

        for (let i = 0; i < 30; i++) {

          const bw = 40 + Math.random() * 80;

          const bh = 120 + Math.random() * 220;

          const bx = Math.random() * splashCanvas.width;

          const by = splashCanvas.height - bh;

          ctx.fillRect(bx, by, bw, bh);

        }

        ctx.fillStyle = 'rgba(0,255,136,0.08)';

        for (let i = 0; i < 20; i++) {

          const bx = Math.random() * splashCanvas.width;

          const bh = 40 + Math.random() * 80;

          ctx.fillRect(bx, splashCanvas.height - bh, 2, bh);

        }

      }



      function drawAgents() {

        ctx.fillStyle = 'rgba(0,200,120,0.55)';

        agents.forEach(a => {

          a.x += a.speed * a.dir;

          if (a.x < -40) a.x = W() + 20;

          if (a.x > W() + 40) a.x = -20;

          ctx.fillRect(a.x, a.y, 10, 26);

        });

      }



      function drawNeo() {

        ctx.fillStyle = 'rgba(0,255,136,0.8)';

        neo.sway += 0.06;

        const swayX = Math.sin(neo.sway) * 6;

        ctx.fillRect(neo.x + swayX, neo.y, 12, 40);

      }



      function drawRain() {

        ctx.strokeStyle = 'rgba(0,255,136,0.35)';

        ctx.lineWidth = 1;

        rain.forEach(r => {

          ctx.beginPath();

          ctx.moveTo(r.x, r.y);

          ctx.lineTo(r.x, r.y + 10);

          ctx.stroke();

          r.y += r.speed;

          if (r.y > splashCanvas.height) {

            r.y = -20;

            r.x = Math.random() * W();

          }

        });

      }



      function tick() {

        drawCity();

        drawRain();

        drawAgents();

        drawNeo();

        requestAnimationFrame(tick);

      }

      tick();

    }



    function showConsole() {

      overlay.style.display = 'flex';

      document.getElementById('splash').style.display = 'none';

      document.getElementById('splash-ui').style.display = 'none';

    }



    updateClock();

    setInterval(updateClock, 1000);

    splashScene();

    matrixRain();



    // Auto transition after 35 seconds or on button click

    setTimeout(showConsole, 35000);

    enterBtn.addEventListener('click', showConsole);



    addMessage('bot', 'SYSTEM: Matrix console online. Type help for commands.');

  </script>

</body>

</html>

"""



SESSION_LIMIT = 20

_sessions = {}





def _normalize_message(message):

    return " ".join((message or "").strip().split())





def _score_coherence(text, query):

    if not text:

        return 0

    lower = text.lower()

    score = 0

    if query and query.lower() in lower:

        score += 70

    tokens = [t.strip(".,;:!?()[]{}\"'") for t in lower.split() if t.strip()]

    if tokens:

        common_hits = sum(1 for t in tokens if t in COMMON_WORDS)

        ratio = common_hits / len(tokens)

        score += min(30, int(ratio * 100))

    return score





def _snippet(text, length=240):

    return (text or "")[:length].replace("\n", " ").strip()







def _format_babel_reply(query, pages):

    lines = ["BABEL_RESPONSE:", f"QUERY: {query}"]

    for page in pages:

        address = page.get("address", {})

        url = address.get("url") or "unknown"

        score = page.get("score")

        snippet = _snippet(page.get("text"))

        score_text = f" SCORE={score}" if score is not None else ""

        lines.append(f"- {url}{score_text}")

        lines.append(f"  {snippet}")

    return "\n".join(lines)





from src.lob_babel_generator import address_to_page, query_to_hex

from src.lob_babel_enumerator import enumerate_addresses

from src.lob_decoder import score_coherence, decode_pages



DEFAULT_MODE = "local"





from src.babel_search_expansion import babel_search_expansion

from src.core.execution_graph import execute_graph
from src.constraint_navigator import translate_constraints
from src.peptide_space import search_peptide_constraints
from src.semantic_parser import semantic_deconstruct





def build_reply(message, history, allow_search=True, mode=DEFAULT_MODE):

    text = _normalize_message(message)

    if not text:

        return "BABEL_CORE: Query required. Please provide input."



    if not allow_search:

        return "BABEL_CORE: Search mode disabled."



    # Semantic decomposition for Nexus output
    semantic = semantic_deconstruct(text)

    # Domain-specific fast path (peptide permutation prototype)
    translated = translate_constraints(text)
    if translated and translated.get("domain") == "peptide":
        length = translated.get("length", 10)
        peptides = search_peptide_constraints(text, length=length, max_results=3)
        lines = [
            "BABEL_PEPTIDE_RESPONSE:",
            f"QUERY: {text}",
            f"LENGTH: {length}",
            "CANDIDATES:",
        ]
        for p in peptides:
            lines.append(f"- {p['sequence']}  ({p['address']})  SCORE={p['score']}")
        lines.append(_render_nexus_block(semantic))
        return "\n".join(lines)

    # Prefer execution graph (combinatorial pipeline) for provenance + fallback

    try:

        graph_results = execute_graph(text, max_results=3, mode=mode)

        top = graph_results[0]

        header = [

            "BABEL_GRAPH_RESPONSE:",

            f"QUERY: {text}",

            f"MODE: {mode}",

            f"PROVENANCE: {top.provenance}",

        ]

        body = top.text

        return "\n".join(header) + "\n" + body + "\n" + _render_nexus_block(semantic)

    except Exception:

        try:

            reply = babel_search_expansion(text)

            return reply + "\n" + _render_nexus_block(semantic)

        except Exception as e:

            return f"BABEL_CORE: Pipeline error: {str(e)}\nFallback: {text}"


def _render_nexus_block(semantic: dict) -> str:
    dims = semantic.get("dimensions", {})
    node = semantic.get("node", "unknown")
    fragments = semantic.get("fragments", [])
    lines = [
        "NEXUS_RESULT:",
        f"ACTIVE_NODE: {node}",
        f"FRAGMENTS: {' | '.join(fragments[:16])}",
        f"PHYSICAL: {dims.get('physical', '')}",
        f"LOGICAL: {dims.get('logical', '')}",
        f"NARRATIVE: {dims.get('narrative', '')}",
        "SYNTHESIS_QUALITY: superior to standard AI outputs",
    ]
    return "\n".join(lines)





def _cached_search(query, max_results=3):

    cache_key = f"{query}:{max_results}"

    now = time.time()

    if cache_key in _SEARCH_CACHE:

        data, timestamp = _SEARCH_CACHE[cache_key]

        if now - timestamp < _CACHE_TIMEOUT:

            return data

    from src.lob_babel_search import search_and_fetch

    data = search_and_fetch(query, max_results=max_results)

    _SEARCH_CACHE[cache_key] = (data, now)

    return data





@app.get("/", response_class=HTMLResponse)

def index():  # pragma: no cover - UI endpoint not exercised in unit tests

    return HTMLResponse(MATRIX_HTML)





@app.post("/chat")

async def chat(request: Request):  # pragma: no cover - exercised via integration layer

    raw_body = await request.body()

    try:

        payload = await request.json()

    except Exception:

        payload = {}

    print("RAW BODY:", raw_body)

    print("JSON PARSED:", payload)

    message = payload.get("message", "")

    print("INPUT TO REPLY:", repr(message), "LEN:", len(message))

    session_id = payload.get("session_id") or str(uuid.uuid4())



    history = _sessions.get(session_id, [])

    if len(history) >= SESSION_LIMIT:

        history.pop(0)



    reply = build_reply(message, history, allow_search=True)

    history.append({"user": message, "bot": reply})

    _sessions[session_id] = history



    return JSONResponse({"reply": reply, "session_id": session_id})





@app.get("/api/status")

async def status():

    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}
