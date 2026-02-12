(() => {
  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("message-input");
  const formEl = document.getElementById("input-form");
  const sessionEl = document.getElementById("session-id");
  const clockEl = document.getElementById("clock");

  const nodeLabel = document.getElementById("node-label");

  const sessionId =
    (crypto && crypto.randomUUID && crypto.randomUUID()) ||
    `sid-${Math.random().toString(16).slice(2, 10)}`;
  sessionEl.textContent = sessionId;

  const samples = [
    {
      url: "https://libraryofbabel.info/book.cgi?hex=3a1f9c",
      alt: "https://libraryofbabel.info/book.cgi?hex=9bd7e2",
      score: 85,
      altScore: 78,
      snippetA: "…THALOS PRIME INTERFACE ACKNOWLEDGED. MATRIX CONSOLE ACTIVE…",
      snippetB: "…COHERENCE STABILIZED. USER INTENT CAPTURED. RETURNING PAGES…",
    },
    {
      url: "https://libraryofbabel.info/book.cgi?hex=4f2bd1",
      alt: "https://libraryofbabel.info/book.cgi?hex=a3ce44",
      score: 88,
      altScore: 74,
      snippetA: "…SYNTHESIS ENGINE ONLINE. GREEN-ON-BLACK RENDER CONFIRMED…",
      snippetB: "…SESSION THREAD LOCKED. STABILITY INDEX 0.92. PROCEED…",
    },
    {
      url: "https://libraryofbabel.info/book.cgi?hex=7c44aa",
      alt: "https://libraryofbabel.info/book.cgi?hex=0f88d2",
      score: 92,
      altScore: 81,
      snippetA: "…BABEL_RESPONSE DELIVERED. HEX MAP RESOLVED. LIVE CLOCK UTC…",
      snippetB: "…CHAT BUFFER PERSISTED. MATRIX RAIN BACKGROUND NOMINAL…",
    },
  ];

  const addMessage = (role, text) => {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "label";
    label.textContent =
      role === "user" ? "YOU" : role === "bot" ? "BABEL" : "SYSTEM";

    const body = document.createElement("pre");
    body.className = "body";
    body.textContent = text;

    wrapper.appendChild(label);
    wrapper.appendChild(body);
    messagesEl.appendChild(wrapper);
    messagesEl.parentElement.scrollTop = messagesEl.parentElement.scrollHeight;
  };

  const detectNode = (text) => {
    const lower = text.toLowerCase();
    if (/[atcg]{10,}/i.test(text) || lower.includes("peptide") || lower.includes("genome")) {
      return "Genomic";
    }
    if (/[0-9+\-*\/=^]/.test(text) || lower.includes("matrix") || lower.includes("logic")) {
      return "Logical";
    }
    if (lower.includes("story") || lower.includes("narrative") || lower.includes("dialog")) {
      return "Narrative";
    }
    return "Universal";
  };

  const buildResponse = (query) => {
    const pick = samples[Math.floor(Math.random() * samples.length)];
    const sections = [
      ["PHYSICAL/CHEMICAL", `${pick.url} SCORE=${pick.score}`, pick.snippetA],
      ["LOGICAL/MATHEMATICAL", `${pick.alt} SCORE=${pick.altScore}`, pick.snippetB],
      [
        "LINGUISTIC/NARRATIVE",
        `${pick.url} SCORE=${pick.score - 3}`,
        "…Narrative coherence stabilized. Context aligned…",
      ],
    ];
    const body = sections
      .map(
        ([title, link, line]) =>
          `${title}:\n- ${link}\n  ${line}\n  SYNTHESIS: relevant | scope: unrestricted`
      )
      .join("\n");
    return `BABEL_NEXUS_RESPONSE:\nQUERY: ${query}\n${body}\nCOHERENCE: structured | ENGINE: LLM-stub | MODE: local preview`;
  };

  const tickClock = () => {
    const now = new Date();
    clockEl.textContent = `${now.toUTCString()}`;
  };

  tickClock();
  setInterval(tickClock, 1000);

  const sendViaApi = async (text) => {
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          domain: "universal",
          constraints: [],
        }),
      });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      return data.reply || buildResponse(text);
    } catch (err) {
      return buildResponse(text);
    }
  };

  formEl.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const value = inputEl.value.trim();
    if (!value) return;
    const node = detectNode(value);
    nodeLabel.textContent = node;
    addMessage("system", "Semantic Deconstruction → Coordinate Mapping → Nexus Assembly");
    addMessage("user", value);
    inputEl.value = "";
    addMessage("bot", await sendViaApi(value));
  });

  inputEl.addEventListener("input", (evt) => {
    nodeLabel.textContent = detectNode(evt.target.value);
  });

  addMessage(
    "system",
    "Matrix console ready. Type a query and press Enter to see the rendered BABEL_RESPONSE."
  );
  addMessage(
    "bot",
    buildResponse('Thalos Prime created by "Tony Ray Macier III"')
  );

  const canvas = document.getElementById("matrix-canvas");
  const ctx = canvas.getContext("2d");
  const glyphs = "01#@$%&*ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const fontSize = 16;
  let drops = [];

  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const columns = Math.floor(canvas.width / fontSize);
    drops = Array.from({ length: columns }, () => 1);
  };

  const draw = () => {
    ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(0, 255, 140, 0.75)";
    ctx.font = `${fontSize}px 'SFMono-Regular','Consolas','Menlo',monospace`;

    for (let i = 0; i < drops.length; i++) {
      const text = glyphs.charAt(Math.floor(Math.random() * glyphs.length));
      ctx.fillText(text, i * fontSize, drops[i] * fontSize);
      if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }
      drops[i]++;
    }
    requestAnimationFrame(draw);
  };

  resize();
  draw();
  window.addEventListener("resize", resize);
})();
