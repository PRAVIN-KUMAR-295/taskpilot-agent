# TaskPilot — Autonomous AI Agent for Everyday Tasks

> **Build Fast with AI: AI Build Challenge 2026**  
> **Problem Statement:** PS-01 — Autonomous Agents for Everyday Apps  
> **Track:** Autonomous Agent Workflow for Productivity & Everyday Tasks

---

## 🌟 Overview

**TaskPilot** is a production-ready autonomous AI productivity agent designed to manage everyday user tasks. Instead of functioning as a simple text chatbot, TaskPilot understands natural-language goals, plans required actions, executes specialized tools, persists tasks and context, performs real-world knowledge searches, and enforces human-in-the-loop approval before executing destructive actions.

---

## 🏗️ Architecture

```
                       ┌───────────────────────────────┐
                       │   Frontend UI (HTML/CSS/JS)   │
                       │   - Chat & Structured Cards   │
                       │   - Human Approval Modals     │
                       │   - Real-Time Health Polling  │
                       └───────────────▲───────────────┘
                                       │ HTTP / JSON (Port 8001)
                                       ▼
                       ┌───────────────────────────────┐
                       │     FastAPI Backend Router    │
                       │     GET /, GET /health        │
                       │     POST /chat                │
                       │     GET /tasks                │
                       └───────────────▲───────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌──────────────────────┐              ┌──────────────────────┐
        │  Autonomous Agent    │              │ Local Task Engine    │
        │  - OpenAI Tool Loop  │              │ (Deterministic Fall- │
        │  - Risk Interceptor  │              │  back for 0-credits) │
        └───────────┬──────────┘              └──────────┬───────────┘
                    │                                    │
                    └──────────────────┬─────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │          Tools Layer          │
                       ├───────────────────────────────┤
                       │ • tool_create_task            │
                       │ • tool_get_tasks              │
                       │ • tool_complete_task          │
                       │ • tool_delete_task (Risky)    │
                       │ • tool_clear_all_tasks (Risky)│
                       │ • tool_search (Live Wikipedia)│
                       └───────────────▲───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌────────────────┐            ┌────────────────┐            ┌────────────────┐
│  Task Service  │            │ Search Service │            │ Memory Service │
│ (tasks.json)   │            │ (Live HTTP API)│            │ (Scrubbed JSON)│
└────────────────┘            └────────────────┘            └────────────────┘
```

---

## 🚀 Key Features

1. **Autonomous Tool Calling**:
   - Understands user intentions and plans tool calls dynamically.
   - Extracts task title, priority (`low`, `medium`, `high`), and due date/time (`tomorrow`, `5:00 PM`, etc.).
2. **Persistent Task Management**:
   - Create, list, filter (`pending` / `completed`), complete, and delete tasks.
   - Persisted safely to disk in `data/tasks.json`.
3. **Live Information Search**:
   - Real-time Wikipedia public API integration (`search_service.py`).
   - Zero fake results; extracts summaries, snippets, and verified source links.
   - Robust timeout and network error handling.
4. **Human-in-the-Loop Approval (Safety Guard)**:
   - High-impact and destructive actions (`delete_task`, `clear_all_tasks`) are automatically intercepted.
   - Returns a structured approval request card with confirmation prompts.
   - Only executes permanent actions after explicit user confirmation.
5. **Memory & Secret Scrubbing**:
   - Retains recent conversation context.
   - Automatically detects and scrubs API keys, bearer tokens, and credentials (`[REDACTED_SECRET]`) before writing to disk.
6. **Resilient Error Handling**:
   - Gracefully handles missing API keys, 401 authentication errors, 429 quota exhaustion, network timeouts, and invalid inputs.
   - Never crashes with an unhandled 500 error.
   - Offline fallback engine enables local testing and demonstration even when OpenAI credit balance is exhausted.
7. **Modern Interactive UI**:
   - Clean, responsive chat interface.
   - Dynamic online/offline health indicator polling `http://127.0.0.1:8001/health`.
   - Structured visual task cards with status badges and due dates.
   - Interactive Human Approval confirmation cards with Confirm/Cancel buttons.
   - Quick suggestion prompt chips for rapid demonstration.

---

## 📂 Project Structure

```
taskpilot-agent/
├── backend/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py       # Persistent JSON task CRUD + due date support
│   │   ├── search_service.py     # Live Wikipedia search with error handling
│   │   └── memory_service.py     # Conversation memory + regex secret scrubber
│   ├── __init__.py
│   ├── agent.py                  # Agent reasoning loop, tool execution, & approval guard
│   ├── config.py                 # Safe environment configuration loader
│   ├── main.py                   # FastAPI backend with CORS & error handling
│   ├── models.py                 # Pydantic schemas (Chat, Tasks, Approvals)
│   ├── requirements.txt          # Python dependencies
│   └── tools.py                  # Tool definitions & risky action registry
├── data/
│   └── tasks.json                # Task persistence store
├── frontend/
│   ├── app.js                    # Chat UI logic, health check, task cards & approvals
│   ├── index.html                # Responsive web interface with quick prompt chips
│   └── style.css                 # Clean modern stylesheet
├── tests/
│   ├── test_agent.py             # Agent workflows, endpoints, approval & error tests
│   └── test_tools.py             # Task CRUD, due date, search, risks, & memory tests
├── .gitignore                    # Ignores .venv, .env, *.log, memory cache
├── LICENSE                       # MIT License
└── README.md                     # Documentation & Hackathon guide
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- A modern web browser (Chrome, Edge, Firefox, Safari)

### 2. Clone / Open Repository
```bash
cd "C:\Users\pravi\OneDrive\Documents\Desktop\taskpilot-agent"
```

### 3. Create & Activate Virtual Environment
```bash
# Windows PowerShell
python -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r backend\requirements.txt
```

---

## 🔑 Environment Variables

Create or update `.env` in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

> **Note:** TaskPilot runs smoothly even if OpenAI credits are temporarily exhausted or offline by leveraging its local deterministic task engine. API keys are never printed, logged, or committed to Git.

---

## 🖥️ Running the Application

### 1. Start the Backend API (Port 8001)

From the project root:
```bash
python -m uvicorn backend.main:app --port 8001 --reload
```
Or from the `backend/` directory:
```bash
cd backend
python -m uvicorn main:app --port 8001 --reload
```

Verify backend health in your browser:
- Status: [http://127.0.0.1:8001/](http://127.0.0.1:8001/)
- Health Check: [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)
- API Docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

### 2. Launch the Frontend UI

You can open `frontend/index.html` directly in any web browser, or serve it via a local static server:
```bash
# Using Python's built-in HTTP server
python -m http.server 3000 --directory frontend
```
Then navigate to: [http://127.0.0.1:3000](http://127.0.0.1:3000)

The UI will automatically connect to `http://127.0.0.1:8001` and display a green **Online** status indicator.

---

## 🧪 Running Tests

Run the comprehensive pytest suite covering all target features:
```bash
pytest -v
```

### Verified Test Suite:
- `test_home_endpoint`: Root API status verification.
- `test_health_endpoint`: Health metrics and task counts.
- `test_chat_invalid_empty_input`: Graceful validation of blank inputs.
- `test_agent_task_creation_workflow`: End-to-end task creation with priority and due date.
- `test_agent_task_listing_workflow`: Retrieval of stored and pending tasks.
- `test_agent_task_completion_workflow`: Task state transitions.
- `test_human_approval_intercepts_risky_deletion`: Risky action interception & approval confirmation.
- `test_chat_endpoint_full_flow`: Chat endpoint communication.
- `test_agent_handles_openai_auth_error`: Resilient handling of 401 Authentication errors.
- `test_agent_handles_openai_rate_limit_error`: Resilient handling of 429 Quota Exhaustion.
- `test_task_creation_with_due_date_and_priority`: Task storage properties.
- `test_task_creation_validation`: Title input constraints.
- `test_task_listing_and_filtering`: Filter by pending/completed.
- `test_task_completion`: Task ID completion logic.
- `test_risky_action_detection_and_deletion`: Safe execution of destructive operations.
- `test_real_search_service`: Live Wikipedia search retrieval.
- `test_search_service_empty_query`: Search validation.
- `test_memory_service_secret_scrubbing`: Key masking (`[REDACTED_SECRET]`).

**Result:** `18 passed in 38s` (100% passing).

---

## 💬 Example User Prompts

| User Prompt | Agent Autonomous Behavior |
| :--- | :--- |
| `"Create a task to prepare my hackathon presentation tomorrow with high priority"` | Extracts title, sets `priority=high`, `due_date=tomorrow`, saves task, and renders task card. |
| `"Show me my pending tasks"` | Retrieves active tasks from `data/tasks.json` and renders interactive cards. |
| `"Complete task #1"` | Updates status to `completed` and returns confirmation. |
| `"Delete task #1"` | **Halts execution.** Displays **Action Approval Required** card asking the user to confirm. |
| `"Search for Artificial Intelligence"` | Queries live Wikipedia API and returns synthesized facts with source citations. |

---

## 🛡️ Security & Privacy

- **No Hardcoded Secrets**: Secrets are loaded exclusively from `.env`.
- **Git Protection**: `.env`, `*.log`, and `data/memory.json` are strictly ignored in `.gitignore`.
- **Automatic Secret Scrubbing**: All messages passed through `memory_service` are checked against secret patterns and sanitized prior to disk storage.
- **Human-in-the-Loop**: Permanent data deletion cannot be triggered silently by prompt injection or model hallucination.

---

## ⚠️ Known Limitations & Future Work

- **OpenAI Quota**: In environments where OpenAI credits are depleted (Error 429), TaskPilot automatically falls back to its deterministic local engine so all everyday task workflows remain fully operational.
- **Calendar Integrations**: Future versions can connect directly to Google Calendar / Outlook APIs for automatic calendar synchronization.
- **Multi-User Support**: Currently designed for single-user local productivity with local JSON persistence; multi-tenant database support (PostgreSQL/SQLite) can be integrated seamlessly.