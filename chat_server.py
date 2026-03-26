"""
mama health chat server
Run from project root: python chat_server.py
"""
import json
import sys
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>mama health</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --sage: #7a9e7e;
    --sage-light: #e8f0e9;
    --sage-dark: #4a6b4e;
    --blush: #f2e8e4;
    --cream: #faf8f5;
    --ink: #1a1a18;
    --ink-muted: #6b6b68;
    --ink-faint: #b8b8b4;
    --white: #ffffff;
    --symptom: #c97b5a;
    --medication: #5a7bc9;
    --lifestyle: #7a9e7e;
    --fallback: #9b8ea8;
    --radius: 18px;
    --radius-sm: 10px;
  }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--cream);
    color: var(--ink);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Header */
  header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 28px;
    background: var(--white);
    border-bottom: 1px solid rgba(0,0,0,0.06);
    flex-shrink: 0;
  }

  .logo-mark {
    width: 38px;
    height: 38px;
    background: var(--sage);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .logo-mark svg { width: 20px; height: 20px; }

  .header-text h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 17px;
    font-weight: 400;
    color: var(--ink);
    letter-spacing: -0.01em;
  }

  .header-text p {
    font-size: 12px;
    color: var(--ink-muted);
    font-weight: 300;
    margin-top: 1px;
  }

  .status-dot {
    width: 7px;
    height: 7px;
    background: var(--sage);
    border-radius: 50%;
    margin-left: auto;
    flex-shrink: 0;
    animation: pulse 2.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
  }

  /* Messages area */
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 28px 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    scroll-behavior: smooth;
  }

  #messages::-webkit-scrollbar { width: 4px; }
  #messages::-webkit-scrollbar-track { background: transparent; }
  #messages::-webkit-scrollbar-thumb { background: var(--ink-faint); border-radius: 4px; }

  /* Welcome state */
  .welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    text-align: center;
    padding: 40px 20px;
    gap: 12px;
  }

  .welcome-icon {
    width: 64px;
    height: 64px;
    background: var(--sage-light);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 8px;
  }

  .welcome h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 22px;
    font-weight: 400;
    color: var(--ink);
  }

  .welcome p {
    font-size: 14px;
    color: var(--ink-muted);
    line-height: 1.6;
    max-width: 340px;
    font-weight: 300;
  }

  .suggestion-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 8px;
  }

  .chip {
    padding: 8px 16px;
    background: var(--white);
    border: 1px solid rgba(0,0,0,0.1);
    border-radius: 20px;
    font-size: 13px;
    color: var(--ink-muted);
    cursor: pointer;
    transition: all 0.18s ease;
    font-family: 'DM Sans', sans-serif;
  }

  .chip:hover {
    background: var(--sage-light);
    border-color: var(--sage);
    color: var(--sage-dark);
    transform: translateY(-1px);
  }

  /* Message bubbles */
  .message-row {
    display: flex;
    gap: 10px;
    animation: fadeUp 0.3s ease forwards;
    opacity: 0;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .message-row.user { flex-direction: row-reverse; }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 500;
    margin-top: 2px;
    align-self: flex-end;
  }

  .avatar.user-av {
    background: var(--ink);
    color: var(--white);
    font-size: 12px;
  }

  .avatar.agent-av {
    background: var(--sage-light);
    color: var(--sage-dark);
    font-size: 11px;
    font-weight: 500;
  }

  .bubble-wrap { display: flex; flex-direction: column; gap: 4px; max-width: 72%; }
  .message-row.user .bubble-wrap { align-items: flex-end; }

  .agent-label {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0 4px;
  }

  .label-symptom   { color: var(--symptom); }
  .label-medication { color: var(--medication); }
  .label-lifestyle  { color: var(--lifestyle); }
  .label-fallback   { color: var(--fallback); }

  .bubble {
    padding: 12px 16px;
    border-radius: var(--radius);
    font-size: 14.5px;
    line-height: 1.65;
    font-weight: 300;
  }

  .bubble.user {
    background: var(--ink);
    color: var(--white);
    border-bottom-right-radius: var(--radius-sm);
  }

  .bubble.agent {
    background: var(--white);
    color: var(--ink);
    border: 1px solid rgba(0,0,0,0.07);
    border-bottom-left-radius: var(--radius-sm);
  }

  .bubble.agent.symptom-bubble   { border-top: 2.5px solid var(--symptom); }
  .bubble.agent.medication-bubble { border-top: 2.5px solid var(--medication); }
  .bubble.agent.lifestyle-bubble  { border-top: 2.5px solid var(--lifestyle); }
  .bubble.agent.fallback-bubble   { border-top: 2.5px solid var(--fallback); }

  /* Escalation warning */
  .escalation-warning {
    background: #fef3ef;
    border: 1px solid #f5c5b0;
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-size: 13px;
    color: #c0522a;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: -8px 0 0 42px;
    animation: fadeUp 0.3s ease forwards;
  }

  /* Typing indicator */
  .typing-row {
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }

  .typing-bubble {
    background: var(--white);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: var(--radius);
    border-bottom-left-radius: var(--radius-sm);
    padding: 14px 18px;
    display: flex;
    gap: 5px;
    align-items: center;
  }

  .dot {
    width: 6px;
    height: 6px;
    background: var(--ink-faint);
    border-radius: 50%;
    animation: bounce 1.2s ease-in-out infinite;
  }
  .dot:nth-child(2) { animation-delay: 0.18s; }
  .dot:nth-child(3) { animation-delay: 0.36s; }

  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-5px); }
  }

  /* Input area */
  .input-area {
    padding: 16px 20px 20px;
    background: var(--white);
    border-top: 1px solid rgba(0,0,0,0.06);
    flex-shrink: 0;
  }

  .input-row {
    display: flex;
    gap: 10px;
    align-items: flex-end;
    background: var(--cream);
    border: 1.5px solid rgba(0,0,0,0.1);
    border-radius: 24px;
    padding: 8px 8px 8px 18px;
    transition: border-color 0.2s;
  }

  .input-row:focus-within { border-color: var(--sage); }

  #user-input {
    flex: 1;
    border: none;
    background: transparent;
    font-family: 'DM Sans', sans-serif;
    font-size: 14.5px;
    font-weight: 300;
    color: var(--ink);
    resize: none;
    outline: none;
    line-height: 1.5;
    max-height: 120px;
    padding: 4px 0;
  }

  #user-input::placeholder { color: var(--ink-faint); }

  #send-btn {
    width: 38px;
    height: 38px;
    background: var(--sage);
    border: none;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.18s ease;
  }

  #send-btn:hover { background: var(--sage-dark); transform: scale(1.05); }
  #send-btn:active { transform: scale(0.96); }
  #send-btn:disabled { background: var(--ink-faint); cursor: not-allowed; transform: none; }
  #send-btn svg { width: 16px; height: 16px; }

  .disclaimer {
    text-align: center;
    font-size: 11px;
    color: var(--ink-faint);
    margin-top: 10px;
    font-weight: 300;
  }

  @media (max-width: 520px) {
    #messages { padding: 18px 14px; }
    .input-area { padding: 12px 14px 16px; }
    .bubble-wrap { max-width: 85%; }
  }
</style>
</head>
<body>

<header>
  <div class="logo-mark">
    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round">
      <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
    </svg>
  </div>
  <div class="header-text">
    <h1>mama health</h1>
    <p>Your personal health assistant</p>
  </div>
  <div class="status-dot"></div>
</header>

<div id="messages">
  <div class="welcome" id="welcome">
    <div class="welcome-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#7a9e7e" stroke-width="1.5" stroke-linecap="round" width="32" height="32">
        <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
      </svg>
    </div>
    <h2>How can I help you today?</h2>
    <p>Ask me about symptoms, medications, or lifestyle guidance. I'll connect you with the right specialist.</p>
    <div class="suggestion-chips">
      <span class="chip" onclick="sendChip(this)">I've had a headache for two days</span>
      <span class="chip" onclick="sendChip(this)">Side effects of ibuprofen?</span>
      <span class="chip" onclick="sendChip(this)">Foods to avoid with high blood pressure</span>
      <span class="chip" onclick="sendChip(this)">How much sleep do I need?</span>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-row">
    <textarea id="user-input" rows="1" placeholder="Ask a health question…" autocomplete="off"></textarea>
    <button id="send-btn" onclick="sendMessage()" title="Send">
      <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
      </svg>
    </button>
  </div>
  <p class="disclaimer">For emergencies, call 112 (EU) or 911 (US). This assistant does not provide medical diagnoses.</p>
</div>

<script>
const messagesEl = document.getElementById('messages');
const inputEl    = document.getElementById('user-input');
const sendBtn    = document.getElementById('send-btn');
const welcomeEl  = document.getElementById('welcome');

const AGENT_META = {
  symptom:    { label: 'Symptom specialist',    initials: 'SY', cls: 'symptom' },
  medication: { label: 'Medication specialist', initials: 'RX', cls: 'medication' },
  lifestyle:  { label: 'Lifestyle coach',       initials: 'LJ', cls: 'lifestyle' },
  fallback:   { label: 'mama health',           initials: 'MH', cls: 'fallback' },
  router:     { label: 'mama health',           initials: 'MH', cls: 'fallback' },
};

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

function sendChip(el) {
  inputEl.value = el.textContent;
  sendMessage();
}

function hideWelcome() {
  if (welcomeEl) welcomeEl.style.display = 'none';
}

function appendUserBubble(text) {
  hideWelcome();
  const row = document.createElement('div');
  row.className = 'message-row user';
  row.innerHTML = `
    <div class="bubble-wrap">
      <div class="bubble user">${escHtml(text)}</div>
    </div>
    <div class="avatar user-av">you</div>`;
  messagesEl.appendChild(row);
  scrollBottom();
}

function showTyping() {
  const row = document.createElement('div');
  row.className = 'typing-row';
  row.id = 'typing';
  row.innerHTML = `
    <div class="avatar agent-av" style="width:32px;height:32px;margin-bottom:0">
      <svg viewBox="0 0 24 24" fill="none" stroke="#4a6b4e" stroke-width="2" width="14" height="14">
        <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
      </svg>
    </div>
    <div class="typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
  messagesEl.appendChild(row);
  scrollBottom();
}

function removeTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

function appendAgentBubble(text, agentType, shouldEscalate) {
  const meta = AGENT_META[agentType] || AGENT_META.fallback;
  const row = document.createElement('div');
  row.className = 'message-row';
  row.innerHTML = `
    <div class="avatar agent-av">${meta.initials}</div>
    <div class="bubble-wrap">
      <span class="agent-label label-${meta.cls}">${meta.label}</span>
      <div class="bubble agent ${meta.cls}-bubble">${formatText(text)}</div>
    </div>`;
  messagesEl.appendChild(row);

  if (shouldEscalate) {
    const warn = document.createElement('div');
    warn.className = 'escalation-warning';
    warn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      If this is a medical emergency, please call 112 (EU) or 911 (US) immediately.`;
    messagesEl.appendChild(warn);
  }
  scrollBottom();
}

function formatText(text) {
  return escHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function scrollBottom() {
  requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight);
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || sendBtn.disabled) return;

  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  appendUserBubble(text);
  showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    removeTyping();
    if (data.error) {
      appendAgentBubble('Sorry, something went wrong: ' + data.error, 'fallback', false);
    } else {
      appendAgentBubble(data.text, data.agent, data.should_escalate);
    }
  } catch (err) {
    removeTyping();
    appendAgentBubble('Could not reach the server. Please check it is running.', 'fallback', false);
  }

  sendBtn.disabled = false;
  inputEl.focus();
}
</script>
</body>
</html>
"""


sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import UserMessage
from src.orchestrator.orchestrator import Orchestrator

orchestrator = Orchestrator()


class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default request logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def do_POST(self):
        if self.path != "/chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        user_text = body.get("text", "").strip()

        try:
            msg = UserMessage(text=user_text, session_id="web-session")
            response = orchestrator.process(msg)
            payload = {
                "text": response.text,
                "agent": response.agent.value,
                "should_escalate": response.should_escalate,
            }
        except Exception as e:
            payload = {"error": str(e)}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))


if __name__ == "__main__":
    port = 8000
    print(f"\n  mama health is running at http://localhost:{port}")
    print("  Open that URL in your browser.")
    print("  Press Ctrl+C to stop.\n")
    server = HTTPServer(("localhost", port), ChatHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
