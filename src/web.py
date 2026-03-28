"""
mama health chat server — multi-session
Run from project root: python web.py
"""
import json
import sys
import uuid
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
    --sage: #7a9e7e; --sage-light: #e8f0e9; --sage-dark: #4a6b4e;
    --cream: #faf8f5; --ink: #1a1a18; --ink-muted: #6b6b68; --ink-faint: #b8b8b4;
    --white: #ffffff; --sidebar-w: 220px;
    --symptom: #c97b5a; --medication: #5a7bc9; --lifestyle: #7a9e7e; --fallback: #9b8ea8;
    --radius: 18px; --radius-sm: 10px;
  }
  body { font-family: 'DM Sans', sans-serif; background: var(--cream); color: var(--ink); height: 100vh; display: flex; overflow: hidden; }

  /* Sidebar */
  #sidebar {
    width: var(--sidebar-w); background: var(--white); border-right: 1px solid rgba(0,0,0,0.07);
    display: flex; flex-direction: column; flex-shrink: 0;
  }
  .sidebar-header {
    padding: 18px 16px 12px; border-bottom: 1px solid rgba(0,0,0,0.06);
    display: flex; align-items: center; gap: 10px;
  }
  .logo-mark { width: 32px; height: 32px; background: var(--sage); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .sidebar-header h1 { font-family: 'DM Serif Display', serif; font-size: 15px; font-weight: 400; }
  .new-chat-btn {
    margin: 12px; padding: 9px 14px; background: var(--sage-light); color: var(--sage-dark);
    border: 1px solid rgba(122,158,126,0.3); border-radius: 10px; cursor: pointer;
    font-family: 'DM Sans', sans-serif; font-size: 13px; font-weight: 500;
    display: flex; align-items: center; gap: 8px; transition: all 0.18s;
  }
  .new-chat-btn:hover { background: var(--sage); color: white; }
  .sessions-label { padding: 4px 16px 6px; font-size: 11px; color: var(--ink-faint); font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; }
  #session-list { flex: 1; overflow-y: auto; padding: 4px 8px; display: flex; flex-direction: column; gap: 3px; }
  .session-item {
    padding: 9px 10px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--ink-muted);
    display: flex; align-items: center; justify-content: space-between; gap: 6px;
    transition: background 0.15s; white-space: nowrap; overflow: hidden;
  }
  .session-item:hover { background: var(--cream); }
  .session-item.active { background: var(--sage-light); color: var(--sage-dark); font-weight: 500; }
  .session-name { overflow: hidden; text-overflow: ellipsis; flex: 1; }
  .del-btn { opacity: 0; font-size: 14px; color: var(--ink-faint); background: none; border: none; cursor: pointer; padding: 0 2px; line-height: 1; flex-shrink: 0; }
  .session-item:hover .del-btn { opacity: 1; }
  .del-btn:hover { color: #c0522a; }

  /* Main area */
  #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  header { padding: 14px 24px; background: var(--white); border-bottom: 1px solid rgba(0,0,0,0.06); display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  #chat-title { font-family: 'DM Serif Display', serif; font-size: 16px; font-weight: 400; }
  .status-dot { width: 7px; height: 7px; background: var(--sage); border-radius: 50%; margin-left: auto; animation: pulse 2.5s ease-in-out infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.85)} }

  #messages { flex: 1; overflow-y: auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 18px; scroll-behavior: smooth; }
  #messages::-webkit-scrollbar { width: 4px; }
  #messages::-webkit-scrollbar-thumb { background: var(--ink-faint); border-radius: 4px; }

  .welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; text-align: center; padding: 40px 20px; gap: 10px; }
  .welcome-icon { width: 56px; height: 56px; background: var(--sage-light); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 6px; }
  .welcome h2 { font-family: 'DM Serif Display', serif; font-size: 20px; font-weight: 400; }
  .welcome p { font-size: 13px; color: var(--ink-muted); line-height: 1.6; max-width: 300px; font-weight: 300; }
  .suggestion-chips { display: flex; flex-wrap: wrap; gap: 7px; justify-content: center; margin-top: 6px; }
  .chip { padding: 7px 14px; background: var(--white); border: 1px solid rgba(0,0,0,0.1); border-radius: 20px; font-size: 12px; color: var(--ink-muted); cursor: pointer; transition: all 0.18s; font-family: 'DM Sans', sans-serif; }
  .chip:hover { background: var(--sage-light); border-color: var(--sage); color: var(--sage-dark); transform: translateY(-1px); }

  .message-row { display: flex; gap: 9px; animation: fadeUp 0.28s ease forwards; opacity: 0; }
  .message-row.user { flex-direction: row-reverse; }
  @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
  .avatar { width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 500; margin-top: 2px; align-self: flex-end; }
  .avatar.user-av { background: var(--ink); color: var(--white); }
  .avatar.agent-av { background: var(--sage-light); color: var(--sage-dark); }
  .bubble-wrap { display: flex; flex-direction: column; gap: 3px; max-width: 70%; }
  .message-row.user .bubble-wrap { align-items: flex-end; }
  .agent-label { font-size: 10px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; padding: 0 4px; }
  .label-symptom{color:var(--symptom)} .label-medication{color:var(--medication)} .label-lifestyle{color:var(--lifestyle)} .label-fallback{color:var(--fallback)}
  .bubble { padding: 11px 15px; border-radius: var(--radius); font-size: 14px; line-height: 1.65; font-weight: 300; }
  .bubble.user { background: var(--ink); color: var(--white); border-bottom-right-radius: var(--radius-sm); }
  .bubble.agent { background: var(--white); color: var(--ink); border: 1px solid rgba(0,0,0,0.07); border-bottom-left-radius: var(--radius-sm); }
  .bubble.agent.symptom-bubble{border-top:2.5px solid var(--symptom)} .bubble.agent.medication-bubble{border-top:2.5px solid var(--medication)} .bubble.agent.lifestyle-bubble{border-top:2.5px solid var(--lifestyle)} .bubble.agent.fallback-bubble{border-top:2.5px solid var(--fallback)}
  .escalation-warning { background:#fef3ef; border:1px solid #f5c5b0; border-radius:var(--radius-sm); padding:9px 13px; font-size:12px; color:#c0522a; display:flex; align-items:center; gap:7px; margin: -6px 0 0 39px; animation: fadeUp 0.3s ease forwards; }
  .typing-row { display:flex; gap:9px; align-items:flex-end; }
  .typing-bubble { background:var(--white); border:1px solid rgba(0,0,0,0.07); border-radius:var(--radius); border-bottom-left-radius:var(--radius-sm); padding:13px 16px; display:flex; gap:5px; align-items:center; }
  .dot { width:5px; height:5px; background:var(--ink-faint); border-radius:50%; animation:bounce 1.2s ease-in-out infinite; }
  .dot:nth-child(2){animation-delay:.18s} .dot:nth-child(3){animation-delay:.36s}
  @keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }

  .input-area { padding: 14px 18px 18px; background: var(--white); border-top: 1px solid rgba(0,0,0,0.06); flex-shrink: 0; }
  .input-row { display:flex; gap:9px; align-items:flex-end; background:var(--cream); border:1.5px solid rgba(0,0,0,0.1); border-radius:22px; padding:7px 7px 7px 16px; transition:border-color 0.2s; }
  .input-row:focus-within { border-color: var(--sage); }
  #user-input { flex:1; border:none; background:transparent; font-family:'DM Sans',sans-serif; font-size:14px; font-weight:300; color:var(--ink); resize:none; outline:none; line-height:1.5; max-height:110px; padding:4px 0; }
  #user-input::placeholder { color: var(--ink-faint); }
  #send-btn { width:36px; height:36px; background:var(--sage); border:none; border-radius:50%; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.18s; }
  #send-btn:hover{background:var(--sage-dark);transform:scale(1.05)} #send-btn:active{transform:scale(.96)} #send-btn:disabled{background:var(--ink-faint);cursor:not-allowed;transform:none}
  .disclaimer { text-align:center; font-size:11px; color:var(--ink-faint); margin-top:8px; font-weight:300; }
</style>
</head>
<body>

<div id="sidebar">
  <div class="sidebar-header">
    <div class="logo-mark">
      <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" width="16" height="16">
        <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
      </svg>
    </div>
    <h1>mama health</h1>
  </div>
  <button class="new-chat-btn" onclick="newSession()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
    New conversation
  </button>
  <div class="sessions-label">Conversations</div>
  <div id="session-list"></div>
</div>

<div id="main">
  <header>
    <span id="chat-title">New conversation</span>
    <div class="status-dot"></div>
  </header>
  <div id="messages"></div>
  <div class="input-area">
    <div class="input-row">
      <textarea id="user-input" rows="1" placeholder="Ask a health question…" autocomplete="off"></textarea>
      <button id="send-btn" onclick="sendMessage()" title="Send">
        <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
          <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
    </div>
    <p class="disclaimer">For emergencies call 112 (EU) or 911 (US). This assistant does not provide medical diagnoses.</p>
  </div>
</div>

<script>
const AGENT_META = {
  symptom:    { label:'Symptom specialist',    initials:'SY', cls:'symptom' },
  medication: { label:'Medication specialist', initials:'RX', cls:'medication' },
  lifestyle:  { label:'Lifestyle coach',       initials:'LJ', cls:'lifestyle' },
  fallback:   { label:'mama health',           initials:'MH', cls:'fallback' },
  router:     { label:'mama health',           initials:'MH', cls:'fallback' },
};

// sessions[id] = { name, messages: [{type, text, agent, escalate}] }
let sessions = {};
let activeId = null;

const messagesEl  = document.getElementById('messages');
const inputEl     = document.getElementById('user-input');
const sendBtn     = document.getElementById('send-btn');
const sessionList = document.getElementById('session-list');
const chatTitle   = document.getElementById('chat-title');

function genId() { return 'session-' + Math.random().toString(36).slice(2,9); }

function newSession() {
  const id   = genId();
  const name = 'Conversation ' + (Object.keys(sessions).length + 1);
  sessions[id] = { name, messages: [] };
  switchSession(id);
  renderSidebar();
}

function switchSession(id) {
  activeId = id;
  chatTitle.textContent = sessions[id].name;
  renderMessages();
  renderSidebar();
  inputEl.focus();
}

function deleteSession(id, e) {
  e.stopPropagation();
  fetch('/session/' + id, { method: 'DELETE' });
  delete sessions[id];
  if (activeId === id) {
    const remaining = Object.keys(sessions);
    if (remaining.length > 0) switchSession(remaining[remaining.length - 1]);
    else newSession();
  } else {
    renderSidebar();
  }
}

function renderSidebar() {
  sessionList.innerHTML = '';
  Object.entries(sessions).forEach(([id, s]) => {
    const el = document.createElement('div');
    el.className = 'session-item' + (id === activeId ? ' active' : '');
    el.onclick = () => switchSession(id);
    el.innerHTML = `<span class="session-name">${escHtml(s.name)}</span>
      <button class="del-btn" onclick="deleteSession('${id}', event)" title="Delete">×</button>`;
    sessionList.appendChild(el);
  });
}

function renderMessages() {
  messagesEl.innerHTML = '';
  const s = sessions[activeId];
  if (!s || s.messages.length === 0) {
    messagesEl.innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="#7a9e7e" stroke-width="1.5" stroke-linecap="round" width="28" height="28">
            <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
          </svg>
        </div>
        <h2>How can I help you today?</h2>
        <p>Ask about symptoms, medications, or lifestyle guidance.</p>
        <div class="suggestion-chips">
          <span class="chip" onclick="sendChip(this)">I've had a headache for two days</span>
          <span class="chip" onclick="sendChip(this)">Side effects of ibuprofen?</span>
          <span class="chip" onclick="sendChip(this)">Foods to avoid with high blood pressure</span>
          <span class="chip" onclick="sendChip(this)">How much sleep do I need?</span>
        </div>
      </div>`;
    return;
  }
  s.messages.forEach(m => renderOneMessage(m, false));
  scrollBottom();
}

function renderOneMessage(m, animate) {
  if (m.type === 'user') {
    const row = document.createElement('div');
    row.className = 'message-row user' + (animate ? '' : ' ready');
    if (!animate) row.style.opacity = '1';
    row.innerHTML = `
      <div class="bubble-wrap"><div class="bubble user">${escHtml(m.text)}</div></div>
      <div class="avatar user-av">you</div>`;
    messagesEl.appendChild(row);
  } else {
    const meta = AGENT_META[m.agent] || AGENT_META.fallback;
    const row = document.createElement('div');
    row.className = 'message-row' + (animate ? '' : ' ready');
    if (!animate) row.style.opacity = '1';
    row.innerHTML = `
      <div class="avatar agent-av">${meta.initials}</div>
      <div class="bubble-wrap">
        <span class="agent-label label-${meta.cls}">${meta.label}</span>
        <div class="bubble agent ${meta.cls}-bubble">${formatText(m.text)}</div>
      </div>`;
    messagesEl.appendChild(row);
    if (m.escalate) {
      const warn = document.createElement('div');
      warn.className = 'escalation-warning';
      warn.style.opacity = '1';
      warn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        If this is a medical emergency, please call 112 (EU) or 911 (US) immediately.`;
      messagesEl.appendChild(warn);
    }
  }
}

function showTyping() {
  const row = document.createElement('div');
  row.className = 'typing-row'; row.id = 'typing';
  row.innerHTML = `
    <div class="avatar agent-av" style="width:30px;height:30px">
      <svg viewBox="0 0 24 24" fill="none" stroke="#4a6b4e" stroke-width="2" width="12" height="12">
        <path d="M12 21C12 21 3 14 3 8a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 13-9 13z"/>
      </svg>
    </div>
    <div class="typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
  messagesEl.appendChild(row);
  scrollBottom();
}

function removeTyping() { const t = document.getElementById('typing'); if (t) t.remove(); }
function scrollBottom() { requestAnimationFrame(() => messagesEl.scrollTop = messagesEl.scrollHeight); }
function escHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function formatText(t) { return escHtml(t).replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*(.*?)\*/g,'<em>$1</em>').replace(/\n/g,'<br>'); }

inputEl.addEventListener('keydown', e => { if (e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} });
inputEl.addEventListener('input', () => { inputEl.style.height='auto'; inputEl.style.height=Math.min(inputEl.scrollHeight,110)+'px'; });

function sendChip(el) { inputEl.value = el.textContent; sendMessage(); }

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || sendBtn.disabled) return;

  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  // Auto-name session after first message
  if (sessions[activeId].messages.length === 0) {
    sessions[activeId].name = text.length > 32 ? text.slice(0,32)+'…' : text;
    chatTitle.textContent = sessions[activeId].name;
    renderSidebar();
  }

  const userMsg = { type: 'user', text };
  sessions[activeId].messages.push(userMsg);
  renderOneMessage(userMsg, true);
  showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, session_id: activeId })
    });
    const data = await res.json();
    removeTyping();
    const agentMsg = {
      type: 'agent',
      text: data.error ? 'Sorry, something went wrong: ' + data.error : data.text,
      agent: data.agent || 'fallback',
      escalate: data.should_escalate || false,
    };
    sessions[activeId].messages.push(agentMsg);
    renderOneMessage(agentMsg, true);
  } catch (err) {
    removeTyping();
    const errMsg = { type:'agent', text:'Could not reach the server. Please check it is running.', agent:'fallback', escalate:false };
    sessions[activeId].messages.push(errMsg);
    renderOneMessage(errMsg, true);
  }

  scrollBottom();
  sendBtn.disabled = false;
  inputEl.focus();
}

// Boot: start with one session ready
newSession();
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
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def do_DELETE(self):
        # /session/<id>
        session_id = self.path.split("/session/")[-1]
        orchestrator.clear_session(session_id)
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path != "/chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))
        text       = body.get("text", "").strip()
        session_id = body.get("session_id", "default")

        try:
            msg      = UserMessage(text=text, session_id=session_id)
            response = orchestrator.process(msg)
            payload  = {
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

def run_server(port: int = 8000) -> None:
    print(f"\n  mama health is running at http://localhost:{port}")
    print("  Open that URL in your browser.")
    print("  Press Ctrl+C to stop.\n")
    server = HTTPServer(("localhost", port), ChatHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")

