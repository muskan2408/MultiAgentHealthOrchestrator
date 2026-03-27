# mama health - Full-Stack AI Engineer Challenge

Welcome, and thank you for your interest in joining mama health! This challenge simulates a real-world task you would encounter as part of our AI team. It will test your ability to design and implement multiagent systems, write effective prompts, and produce clean, maintainable Python code.

We respect your time and have designed this exercise to be completed in **4-6 hours**. Please don't feel the need to build a perfect, production-ready system. We're most interested in your **prompt engineering skills**, your **architectural thinking around agents**, and how you write **clean, well-structured Python code**.

Good luck!

---

## The Business Context

mama health operates conversational AI systems that guide patients through complex healthcare journeys. Our platform relies on multiple specialized AI agents working together—each responsible for a specific domain (e.g., symptom triage, medication guidance, appointment scheduling).

A key challenge we face is **agent orchestration**: ensuring that user queries are routed to the right specialist agent, that agents can hand off to each other gracefully, and that the overall conversation remains coherent and helpful.

We're looking for engineers who can design robust multiagent architectures and craft prompts that make each agent reliable, consistent, and safe.

---

## Your Mission

Your mission is to build a **multiagent orchestration system** where a central "router" agent delegates user queries to specialized sub-agents. The system should demonstrate:

1. **Effective prompt engineering** for each agent role
2. **Clean agent orchestration logic** in Python
3. **Proper use of an LLM wrapper** (litellm) for model interactions
4. **Well-structured, typed, and testable code**

---

## The Technology Stack

* **Language:** Python 3.10+
* **LLM Interface:** `litellm` (with Gemini API via Google AI Studio)
* **Typing:** Pydantic for data models, Python type hints throughout
* **Testing:** `pytest`
* **Optional:** `asyncio` for concurrent agent calls

---

## Core Tasks

### 1. Setup

- Clone this repository.
- Create a virtual environment and install dependencies.
- Generate a free Gemini API key from **Google AI Studio**: https://aistudio.google.com/apikey
- Create a `.env` file with your API key.

### 2. Design the Agent Architecture

Create a multiagent system with the following components:

**Router Agent:** The entry point that analyzes user queries and decides which specialist agent should handle them. It should:
- Classify the intent of the user's message
- Route to the appropriate specialist agent
- Handle cases where no specialist is appropriate (fallback response)

**Specialist Agents (implement at least 3):**
- **Symptom Agent:** Handles questions about symptoms, their severity, and when to seek care
- **Medication Agent:** Answers questions about medications, dosages, interactions, and side effects
- **Lifestyle Agent:** Provides guidance on diet, exercise, and daily management of chronic conditions

Each agent should have a distinct personality and expertise scope, enforced through careful prompt design.

### 3. Implement the Orchestration Layer

Build the Python infrastructure to support agent interactions:

- **Agent base class or protocol** defining the interface all agents must implement
- **Router logic** that uses the LLM to classify and delegate
- **Conversation context management** so agents have access to relevant history
- **Response synthesis** to ensure final outputs are coherent

Use `litellm` to interact with the Gemini API. Structure your prompts carefully—this is a core evaluation criterion.

### 4. Prompt Engineering

This is the heart of the challenge. For each agent, craft prompts that:

- Clearly define the agent's role, expertise boundaries, and personality
- Include guardrails to prevent the agent from answering outside its domain
- Handle edge cases (ambiguous queries, multi-topic questions, inappropriate requests)
- Maintain a consistent, helpful tone appropriate for healthcare contexts

**Document your prompt design decisions.** We want to understand *why* you structured your prompts the way you did.

### 5. Code Quality

- **Typing:** Use Python type hints and Pydantic models throughout
- **Structure:** Organize code into logical modules (`agents/`, `orchestrator/`, `models/`, etc.)
- **Unit Tests:** Write tests for your routing logic and at least one agent's core behavior
- **Documentation:** Include docstrings and a clear README explaining your architecture

---

## Example Interaction

```
User: "I've been having stomach cramps after taking my medication. Should I be worried?"

[Router analyzes: symptoms + medication interaction → routes to Symptom Agent with Medication Agent context]

Symptom Agent: "Stomach cramps can sometimes occur with certain medications.
Could you tell me which medication you're taking and when the cramps typically occur?
If the pain is severe or accompanied by other symptoms like fever or blood,
please contact your healthcare provider immediately."
```

---

## What We're Looking For

- **Prompt Engineering Excellence:** Clear, well-structured prompts that produce consistent, appropriate responses. We'll evaluate how you handle edge cases and enforce agent boundaries.
- **Clean Python Code:** Well-organized, typed, and readable code. We value simplicity over cleverness.
- **Architectural Thinking:** How you structure the agent system, handle handoffs, and manage conversation state.
- **Practical Testing:** Tests that verify meaningful behavior, not just coverage metrics.
- **Documentation:** Clear explanations of your design decisions, especially around prompts.

---

## Deliverables

Please submit a link to your GitHub repository. **Keep the repository private** and send an invite to **johannes.unruh@mamahealth.io** (tj-mm) and **lorenzo.famiglini@mamahealth.io** (lollomamahealth) a short notification email to **mattia.munari@mamahealth.io**.

The repository should contain:

1. **`src/`** directory - All source code with clear module organization
2. **`tests/`** directory - Unit tests for routing and agent logic
3. **`prompts/`** directory - Your prompt templates (can be `.txt`, `.md`, or `.py` files)
4. **`requirements.txt`** - All dependencies with pinned versions
5. **`README.md`** - Updated with:
   - **Architecture Overview:** Diagram or description of your agent system
   - **Prompt Design Decisions:** Explain your approach to prompt engineering
   - **Setup Instructions:** How to run and test your system
   - **Example Conversations:** 3-5 example interactions demonstrating the system

---

## Optional "Go the Extra Mile" Tasks

Have extra time? Want to impress us further? Consider one of the following (these are **completely optional**):

- **Agent Handoffs:** Implement explicit handoff between agents when a query spans multiple domains (e.g., Medication Agent hands off to Symptom Agent mid-conversation).
- **Streaming Responses:** Use async/streaming to deliver responses progressively.
- **Evaluation Framework:** Build a simple evaluation harness that tests your agents against a set of predefined queries and expected behaviors.
- **Prompt Versioning:** Implement a system to version and A/B test different prompt variations.
- **Guardrails Implementation:** Add explicit safety checks for detecting and handling requests for medical advice that should be escalated to a human.
- **Observability:** Add logging/tracing to track which agents handled which queries and measure response quality.
- **Use [`jmux`](https://github.com/jaunruh/jmux)**: Use the `jmux` package to retrieve partial LLM results early and take advantage of the partial results to optimize code flow.
