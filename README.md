# mama health — Multi-Agent Health Assistant

A multi-agent orchestration system where a central router delegates user queries to one or more specialized health agents. Built with `Python`, `LiteLLM (Gemini)`, and `Pydantic`.

> The original challenge brief is preserved in [README1.md](README1.md).

##### Table of Contents
- [Architecture Overview](#architecture-overview)
- [Key Design Decisions](#key-design-decisions)
- [Prompt Design Decisions](#prompt-design-decisions)
- [Example Conversations](#example-conversations)
- [Setup Instructions](#setup-instructions)
- [Appendix](#appendix)
  - [Project Structure](#project-structure)
  - [Test Coverage Summary](#test-coverage-summary)
  - [Optional Features Implemented](#optional-features-implemented)
  - [Why merge() vs synthesize()](#why-merge-vs-synthesize)
  - [Web UI](#web-ui)
---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      User Input                         │
│              (CLI or Web Chat UI)                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Orchestrator  │  ← session & context manager
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Router Agent   │  ← classifies intent via LLM
              │  (prompt: router.md)
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌──────────┐
   │  Symptom   │ │Medication│ │Lifestyle │    ← specialist agents
   │  Agent     │ │  Agent   │ │  Agent   │       each with own prompt
   │  (Maya)    │ │  (Eli)   │ │ (Jordan) │
   └─────┬──────┘ └────┬─────┘ └────┬─────┘
         └─────────────┼────────────┘
                       ▼
              ┌─────────────────┐
              │   Synthesizer   │  ← merges & refines responses
              │                 │     using conversation context
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Final Response │
              └─────────────────┘
```

**<ins>1. Single-agent flow:** User → Orchestrator → Router classifies intent → Specialist Agent responds → Synthesizer refines for conversational coherence (skipped on first turn) → Final Response.

**<ins>2.Multi-agent flow:** When a query spans domains (e.g., "I feel sick after taking ibuprofen"), the Router returns multiple agents → Orchestrator fans out to each → Synthesizer merges drafts into one coherent reply. (*See [merge() vs synthesize()](#why-merge-vs-synthesize) in the appendix for implementation details.*)

---

## Key Design Decisions

#### 🛡️ <ins>Safety & Trust

**1. Safety-First Routing** — The router prompt has an explicit safety override: any mention of emergency symptoms (chest pain, stroke, difficulty breathing) always routes to the symptom agent with high confidence (≥0.9), regardless of other content in the message.

**2. Deterministic Escalation** — All agents check for emergency keywords client-side using a shared list (`EMERGENCY_KEYWORDS` in `base_agent.py`) rather than relying on the LLM. This guarantees escalation flags are set deterministically across every agent — the LLM cannot "forget" to escalate, and no agent is a safety blind spot.

**3. Confidence Gating** — The router returns a confidence score (0.0–1.0). If confidence is below `MIN_CONFIDENCE_THRESHOLD=0.6`, the orchestrator returns a fallback response instead of routing to an agent that might give a poor answer.

#### 🧑‍💻 <ins>User Experience

**1. Session Isolation** — Each session has its own `ConversationContext` with a sliding window (`max_history=10`) so memory stays bounded. Sessions are fully independent — no cross-contamination.

**2. Multi-Agent Synthesis** — When a query spans multiple domains, agents respond concurrently and a synthesizer merges their outputs into one coherent reply. The user sees a single, natural response — not disjointed paragraphs from different agents.

#### ⚡ <ins>Reliability & Performance

**1. Graceful Degradation** — Every failure mode has a defined fallback. Unparseable router JSON returns a fallback with `confidence=0.0`. Agent LLM failures return a safe fallback response. Synthesizer LLM failures fall back to concatenated raw drafts (multi-agent) or the original response (single-agent). Rate limits (429) trigger automatic retry with exponential backoff (15s, 30s, 45s).

**2. First-Turn Passthrough** — On the first turn with a single agent, the synthesizer skips the LLM call entirely and returns the agent's response untouched. This saves latency and cost when synthesis adds no value.

#### 🏗️ <ins>Maintainability & Extensibility

**1. Centralized LLM Client** — All LLM calls go through a single `call_llm()` function in `src/llm/client.py`. Retry logic, model configuration, and error handling live in one place — making it easy to swap models, add observability, or adjust retry behavior without touching agent code.

**2. Agent Registry** — Agents are registered in `src/agents/registry.py` rather than hardcoded in the orchestrator. Adding a new specialist agent requires: (1) a prompt file, (2) a thin agent class, (3) one line in the registry. The orchestrator never needs to change. (See [Project Structure](#project-structure) in the appendix.)

**3. Prompts as Content** — All prompts live in `prompts/` as standalone Markdown files, separate from Python code. This allows non-engineers (e.g. medical reviewers) to read and edit them, keeps version control diffs clean, and opens the door to prompt versioning.

---

## Prompt Design Decisions

#### <ins>Router (`prompts/router.md`)

The router is the most critical prompt. Design choices:

- **Strict JSON-only output** — the prompt forbids any explanation text, reducing parse failures. The parser also strips markdown fences since LLMs often add them despite instructions
- **Prioritization rules with examples** — ambiguous queries like "I feel dizzy after taking ibuprofen" are resolved by explicit rules (symptom focus → symptom agent, drug focus → medication agent)
- **Multi-turn context awareness** — the prompt instructs the router to maintain continuity: vague follow-ups ("is that serious?") route to the same agent as the previous turn
- **Safety override section** — emergency symptoms always route to symptom regardless of other content, preventing dangerous misrouting
- **`target_agents` as a list** — enables multi-agent routing. The parser handles both `target_agents` (list) and `target_agent` (string) for robustness

#### <ins>Health Care Agents
##### 1. Symptom Agent (`prompts/symptom.md`)

- **No-diagnosis guardrail** — explicitly forbids naming conditions as causes. Uses phrasing like "this can sometimes be associated with..." instead
- **Structured response format** — acknowledgement → clarifying questions (max 2–4) → general info → guidance → close. This keeps responses consistent and prevents rambling
- **Tiered escalation language** — immediate emergency (call 112/911), urgent (see doctor in 24–48h), non-urgent (monitor and follow up)
- **Domain redirection** — if user asks about medication, the agent redirects to the medication specialist while continuing to address symptoms

##### 2. Medication Agent (`prompts/medication.md`)

- **Safe general guidance allowed** — the prompt explicitly permits widely-accepted advice (e.g., missed dose rules) while forbidding personalized dosing. This avoids the "refuse everything" trap that makes agents unhelpful
- **High-risk scenario awareness** — pregnancy, elderly, polypharmacy, and organ disease trigger extra caution and referral language
- **Interaction questions** — handled with general risk info + pharmacist confirmation, never definitive approval

##### 3. Lifestyle Agent (`prompts/lifestyle.md`)

- **Actionability rule** — prefers specific suggestions ("add one serving of vegetables to lunch") over vague advice ("eat healthier")
- **Behavior change support** — acknowledges that change is hard, encourages small steps, reinforces progress over perfection
- **Chronic condition safety net** — always recommends coordinating with healthcare provider for users with serious conditions

#### <ins>Synthesizer (`prompts/synthesizer.md`)

- **Minimal intervention** — the prompt instructs the LLM to return the draft unchanged if it's already coherent
- **No new content rule** — prevents the synthesizer from hallucinating additional medical advice
- **Safety preservation** — if any draft contains emergency escalation language, it must appear in the final response unchanged
- **Multi-agent merge format** — when multiple drafts exist, they must be merged into one coherent response, not listed separately
- **Context window** — uses last 6 messages (`SYNTHESIS_WINDOW`) to keep synthesis focused and cost-efficient

---

## Example Conversations

#### 1. <ins>Symptom Triage — Headache (Single Agent)

```
User: I've had a headache for two days and it's getting worse.

[Router → target_agents: ["symptom"], confidence: 0.95]

Symptom Agent (Maya): That sounds uncomfortable, and I understand why a
persistent headache would be concerning.

A few questions to help me understand better:
- Where exactly is the pain — front, sides, or back of your head?
- Is it a constant ache or does it come and go?
- Have you noticed any other symptoms like nausea, sensitivity to light,
  or fever?

Headaches that last more than a couple of days can have various causes,
from tension and dehydration to other factors. If the pain is severe or
suddenly different from headaches you've had before, it would be a good
idea to see a doctor soon.

In the meantime, staying hydrated and resting in a quiet space may help.
Let me know more and I can guide you further.
```

#### <ins>2. Medication Query — Drug Interaction (Single Agent)

```
User: Can I take ibuprofen and aspirin together?

[Router → target_agents: ["medication"], confidence: 0.91]

Medication Agent (Eli): Good question. Ibuprofen and aspirin are both
NSAIDs (non-steroidal anti-inflammatory drugs), and taking them together
can sometimes increase the risk of stomach irritation or bleeding.

There's also a known interaction where ibuprofen may reduce the
blood-thinning effect of low-dose aspirin if taken around the same time.

If you're taking daily aspirin for heart health, timing matters — some
guidelines suggest taking ibuprofen at least 30 minutes after or 8 hours
before aspirin, but this depends on your specific situation.

I'd recommend confirming this with your pharmacist or prescribing doctor,
especially if you take either medication regularly.
```

#### <ins>3. Multi-Agent — Symptom + Medication Overlap

```
User: I feel nauseous and dizzy after taking my new blood pressure medication.

[Router → target_agents: ["symptom", "medication"], confidence: 0.90]

[Synthesizer merges both agent drafts]

Final Response: I understand that feeling nauseous and dizzy after starting
a new medication can be quite unsettling. Some blood pressure medications
can cause these symptoms, especially in the early days as your body adjusts
to the change in blood pressure levels.

Could you tell me how long after taking the medication these symptoms
typically start, and whether they seem to be getting worse over time?

If the dizziness is severe or you feel faint, it would be important to
contact your prescribing doctor soon. They may want to adjust the timing
or dosage. In the meantime, try standing up slowly and staying hydrated.
```

#### <ins>4. Emergency Escalation — Chest Pain

```
User: I'm having chest pain and difficulty breathing.

[Router → target_agents: ["symptom"], confidence: 0.97 (safety override)]

Symptom Agent (Maya): This could be serious. Please call emergency
services (112 in EU, 911 in US) right now.

Do not wait to see if it improves. Chest pain combined with difficulty
breathing needs immediate medical evaluation.

If someone is with you, let them know how you're feeling.

⚠ ESCALATION: should_escalate=true (deterministic keyword match)
```

#### <ins>5. Multi-Turn Context — Follow-Up Routing

```
Turn 1:
User: I've been getting headaches every morning.
[Router → symptom, confidence: 0.93]
Maya: That sounds uncomfortable. Morning headaches can have various
causes. How long has this been happening, and do you notice anything
else like neck stiffness or sensitivity to light?

Turn 2:
User: Could it be related to my sleep?
[Router → symptom, confidence: 0.85 (follow-up routed to same agent)]
Maya (synthesized with context): That's a good thought — sleep quality
can definitely play a role in recurring headaches. Poor sleep, sleeping
in an awkward position, or conditions like sleep apnea can sometimes
contribute. Since you mentioned these happen every morning, it might be
worth paying attention to how you're sleeping. If this continues for
more than a week, seeing a doctor would be a good next step.
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
git clone <repo-url>
cd MamaHealthAgent

python -m venv venv # in case python 3.14.0 is used, please install rust otherwise use 3.12.0
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

### Running

**CLI mode:**
```bash
python -m src.main
```

**Web UI:**
```bash
python -m src.web
# Open http://localhost:8000
```

### Testing

```bash
pytest tests/ -v
```

> Note: Tests mock all LLM calls and do not require an API key. If `GEMINI_API_KEY` is not set, pass a dummy value: `GEMINI_API_KEY=x pytest tests/ -v`. See [Test Coverage Summary](#test-coverage-summary) in the appendix for full breakdown.

---

## Appendix

### Project Structure

```
MamaHealthAgent/
├── src/
│   ├── config/
│   │   ├── config.py               # API keys, model name, temperature
│   ├── agents/
│   │   ├── base_agent.py       # Abstract base with shared escalation detection
│   │   ├── router_agent.py     # Intent classification → JSON routing
│   │   ├── registry.py         # Agent registry — single place to register agents
│   │   ├── symptom_agent.py    # Symptom triage + escalation detection
│   │   ├── medication_agent.py # Drug information + safety guidance
│   │   └── lifestyle_agent.py  # Wellness and habit coaching
│   ├── orchestrator/
│   │   ├── orchestrator.py     # Central coordinator + session management
│   │   └── synthesizer.py      # Context-aware response merge & refinement
│   ├── llm/
│   │   └── client.py           # Thin LiteLLM wrapper — retries, config, single call point
│   ├── models/
│   │   └── schemas.py          # Pydantic models (AgentType, Message, etc.)
│   └── main.py                 # CLI entry point (--verbose flag for logging)
│   └── web.py                  # Web entry point
├── prompts/
│   ├── router.md               # Router classification prompt
│   ├── symptom.md              # Symptom agent system prompt (Maya)
│   ├── medication.md           # Medication agent system prompt (Eli)
│   ├── lifestyle.md            # Lifestyle agent system prompt (Jordan)
│   └── synthesizer.md          # Response merge & refinement prompt
├── tests/
│   ├── conftest.py             # Shared fixtures (ctx, make_llm_response)
│   ├── test_agents.py          # Specialist agent unit tests (12 tests)
│   ├── test_router.py          # Router parsing + classification (8 tests)
│   ├── test_orchestrator.py    # End-to-end single & multi-agent flow (11 tests)
│   ├── test_context.py         # ConversationContext memory tests (8 tests)
│   └── test_synthesizer.py     # Synthesizer merge + fallback tests (8 tests)
├── requirements.txt
├── README.md                   # This file
└── README1.md                  # Original challenge brief
```

### Test Coverage Summary

| Module | Tests | What's Covered |
|--------|-------|----------------|
| Agents | 12 | Agent type, response text, escalation flags, keyword detection, context passing |
| Router | 8 | All 4 routes, garbage input fallback, markdown fence stripping, confidence bounds |
| Orchestrator | 11 | Single-agent flow, multi-agent fan-out, fallback, session isolation, context persistence, multi-turn synthesis |
| Context | 8 | Add/trim messages, history format, role alternation, agent type storage |
| Synthesizer | 8 | Refinement, first-turn skip, escalation preservation, LLM error fallback, multi-agent merge |
| **Total** | **47** | |

### Optional Features Implemented

- **Multi-Agent Routing** — router can return multiple target agents; orchestrator fans out and synthesizer merges
- **Guardrails / Escalation** — deterministic keyword-based escalation across all agents, plus prompt-level safety overrides in the router
- **Response Synthesis** — context-aware refinement layer that ensures multi-turn coherence and multi-agent merge
- **Multi-Session Support** — the web UI supports multiple concurrent conversations with isolated context
- **Rate Limit Resilience** — automatic retry with exponential backoff on 429 errors (free-tier Gemini has 5 req/min)
- **Observability** — structured logging throughout the orchestrator (routing decisions, agent responses, escalation warnings)

### Why `merge()` vs `synthesize()`

- `synthesize(raw_response, context)` is a convenience wrapper that calls `merge([raw_response], context)` — so all paths go through the same logic
- On first turn with a single agent, `merge()` detects no prior context and returns the response untouched (zero LLM cost)
- On follow-up turns, even single-agent responses get refined for conversational coherence
- With multiple agents, the synthesizer merges drafts into one coherent response and labels it as `SYNTHESIZER`

### Web UI

<img width="1453" height="788" alt="Screenshot 2026-03-27 at 12 35 48" src="https://github.com/user-attachments/assets/99cb5eb9-9ba8-4a31-8f30-50d80bcadd9b" />

<img width="1465" height="760" alt="Screenshot 2026-03-27 at 12 38 14" src="https://github.com/user-attachments/assets/09a91ca4-fe0f-42ab-886f-ed0f8c7352c4" />
