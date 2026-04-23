# 🎬 AutoStream AI Sales Agent

> **ServiceHive Inflx Internship Assignment** — Social-to-Lead Agentic Workflow  
> Built with **LangGraph** + **Gemini 1.5 Flash** + **FAISS RAG**

---

## 📌 Overview

This project implements a **Conversational AI Agent** for AutoStream, a fictional SaaS video editing platform. The agent:

- 🧠 **Classifies intent** — greeting / product inquiry / high intent
- 📚 **Answers questions via RAG** — retrieves accurate info from a local knowledge base
- 🎯 **Captures leads** — collects name, email, platform, then fires a mock API
- 🔁 **Maintains state** — remembers the full conversation across turns

---

## 🚀 How to Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/autostream-agent.git
cd autostream-agent
```

### 2. Create a virtual environment (at the project root)

Keep the venv **next to** `backend/` and `frontend/` (not inside `backend/`). That is the usual layout: one environment for the whole repo, imports still use the `backend` package when you run from the root.

```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Mac/Linux:
source .venv/bin/activate
```

You can name the folder `venv` or `.venv`; both are ignored by Git (see `.gitignore`).

### 3. Install dependencies
```bash
pip install -r backend/requirements.txt
```
> ⚠️ First install may take 1-2 minutes to download the embedding model (~90MB).

### 4. Set Up Your API Key

Get a **free** Gemini API key at: https://aistudio.google.com/app/apikey

```bash
cp .env.example .env
# Now edit .env and paste your key:
# GEMINI_API_KEY=your_key_here
```

### 5. Run the agent (choose one)

**Terminal CLI** (from project root):
```bash
python -m backend
```

### Optional: Debug mode (shows intent in the terminal)
```bash
python -m backend --debug
```

**Web UI** — run the API and the Vite app (two options):

1. **Two terminals (recommended for debugging)**  
   Terminal A — API (always from the **project root** — the folder that contains `backend/`):
   ```bash
   # Either:
   python run_api.py
   # Or:
   uvicorn backend.main_api:app --reload --host 127.0.0.1 --port 8000
   ```
   > If you see `No module named 'backend'`, your shell is not in the project root; use `cd` to that folder, or run `python run_api.py` which forces the correct directory.
   Terminal B — UI (from `frontend/`):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```  
   Open the URL Vite shows (e.g. `http://127.0.0.1:5173`). The dev server proxies `/api` to the API on port 8000.

2. **One command from `frontend/`** (starts API + Vite together):
   ```bash
   cd frontend
   npm install
   npm run dev:full
   ```

### View captured leads
- **CLI:** type `leads` during a chat, or read `backend/leads_log.json`.  
- **Web:** use the **Leads** tab in the UI.

---

## 🌐 Deploy on Render (API + static site, two services)

The repo includes a [`render.yaml`](render.yaml) [Blueprint](https://docs.render.com/blueprint-spec) that defines:

| Service        | Type        | What it runs |
|----------------|------------|--------------|
| `autostream-api` | Web (Python) | `python backend/render_entry.py` (listens on `$PORT`) |
| `autostream-web` | Static        | Vite build output in `frontend/dist` |

**Important — Start command (API):** You must run the file with **Python**, exactly one of:

| Root Directory in Render | Start Command |
|--------------------------|---------------|
| Empty (repo root, recommended) | `python backend/render_entry.py` |
| `backend` | `python render_entry.py` |

**Wrong:** `render_entry.py` by itself — Render will try to execute it like a shell binary and you get `command not found` (exit 127). **Right:** always prefix with `python` (or `python3`).

**Important — Root Directory (API web service):** **Root Directory** should be the **repository root** (empty / `.` / leave blank), **not** `backend/`, unless you intentionally use the second row in the table above. If root is `backend/` by mistake, you get `ModuleNotFoundError: No module named 'backend'`. If you use repo root, the start command `python backend/render_entry.py` runs from the folder that *contains* the `backend` package.

**Which env var goes where**

| Variable | Set on | Value |
|----------|--------|--------|
| `GEMINI_API_KEY` | **API (web) only** | Your Gemini key |
| `CORS_ORIGINS` | **API (web) only** | **Static site** URL, e.g. `https://auto-stream-itfv.onrender.com` (the page users open — *not* the API URL) |
| `VITE_API_BASE` | **Static site only** | **API** URL, e.g. `https://auto-stream-backend.onrender.com` (no trailing slash) |

Do **not** put `CORS_ORIGINS` on the static service or `VITE_API_BASE` on the API — they are read in the wrong place and will not work.

### One-time setup (in the Render Dashboard)

1. **Connect the repo** and use **New → Blueprint** (or paste `render.yaml`), or create two services manually with the same build/start/publish as in the file.

2. **API service (`autostream-api`) — environment**
   - **`GEMINI_API_KEY`**: your Google AI / Gemini key (mark as *Secret*).  
   - **`CORS_ORIGINS`**: the **static site’s** public origin (where the UI is hosted), e.g. `https://your-frontend.onrender.com` (no path). You can list several, comma‑separated. **Do not** set this to your API’s URL.  
   - **`PYTHON_VERSION`**: e.g. `3.12.0` (see `runtime.txt` / `render.yaml`) — avoid leaving Render on a very new default (e.g. 3.14) if dependencies lag.

3. **Deploy the API first** and copy its public URL, e.g. `https://autostream-api.onrender.com`.

4. **Static site (`autostream-web`) — environment**
   - **`VITE_API_BASE`**: the API **origin only**, e.g. `https://autostream-api.onrender.com` (no trailing slash). Vite bakes this in at build time, so the static site must be rebuilt after you set or change it.

5. **Link them**
   - Set `CORS_ORIGINS` on the API to your **static** URL.  
   - Set `VITE_API_BASE` on the static site to your **API** URL.  
   - Trigger a **new deploy** for the static site so the bundle picks up `VITE_API_BASE`.

6. **Cold starts (free tier)** The API may sleep when idle; the first request after sleep can be slow. For heavier RAG/embedding, consider a paid instance with more RAM.

**If you see 500 or `API_KEY_INVALID` from Gemini**

- Confirm **`GEMINI_API_KEY`** (or `GOOGLE_API_KEY`) is on the **API web service** only, then **Save** and **Manual Deploy** that service. Open your API’s `/health` in a browser; the JSON should show `"gemini_key_configured": true`.
- **No** leading/trailing spaces in the value (we strip in code, but check in Render).
- In [Google AI Studio](https://aistudio.google.com/apikey), create a new key, ensure **Generative Language API** is allowed for the project, and avoid restrictions that block **server-side** use (e.g. wrong referrers) until it works.
- In the browser, the chat bubble now includes the first part of the server error when the API returns 500—use that plus **API → Logs** on Render to debug.

### Manual alternative (no Blueprint)

- **Web service:** Root directory = **repo root**. Build: `pip install -r backend/requirements.txt`. Start: `python backend/render_entry.py` (or `uvicorn` only if the process cwd is the repo root). Health check path: `/health`.  
- **Static site:** Build: `cd frontend && npm install && npm run build`. Publish directory: `frontend/dist`. Set `VITE_API_BASE` to the **API** URL.

---

## 💬 Example Conversation

```
👤 You: Hi there!
🤖 Agent: Hi! 👋 I'm the AutoStream AI assistant. How can I help you today?

👤 You: What's the price for the Pro plan?
🤖 Agent: The AutoStream Pro Plan is $79/month and includes:
         • Unlimited videos per month
         • 4K resolution
         • AI captions
         • 24/7 live support
         Would you like to get started?

👤 You: That sounds great, I want to try the Pro plan for my YouTube channel
🤖 Agent: Great, I'd love to get you started! 🎬
         Could you please share your full name?

👤 You: Ravi Kumar
🤖 Agent: Nice to meet you, Ravi! 👋
         What's your email address so we can set up your account?

👤 You: ravi@gmail.com
🤖 Agent: Perfect! Which creator platform do you primarily use?

👤 You: YouTube
🤖 Agent: 🎉 You're all set, Ravi! We've captured your details...

==================================================
🎯 LEAD CAPTURED SUCCESSFULLY
  Name     : Ravi Kumar
  Email    : ravi@gmail.com
  Platform : YouTube
==================================================
```

---

## 🏗️ Architecture Explanation

### Why LangGraph?

LangGraph was chosen over plain LangChain or AutoGen because it enables **explicit state machine control** — the conversation is not just a prompt loop but a structured graph of nodes. This is critical for an agentic workflow where:

1. We need to know *exactly* when to trigger the lead capture tool (only when all 3 fields are collected)
2. We need to persist state (collected name, email, platform) across multiple turns without relying purely on LLM memory
3. Conditional routing logic is clean and testable — each node is a pure Python function

### How State Is Managed

State is a **typed Python dictionary** (`AgentState`) passed through the graph at every turn:

```python
{
  "messages": [...],          # Full conversation history (LangChain messages)
  "intent": "high_intent",   # Classified intent of latest message
  "lead_name": "Ravi",       # Collected name (None until provided)
  "lead_email": None,        # Collected email
  "lead_platform": None,     # Collected platform
  "lead_captured": False,    # Tool fire flag
  "awaiting_lead_field": "email"  # Which field to ask next
}
```

The graph flow is:

```
User Input
    │
    ▼
[intent_router] ──► classify intent
    │
    ├──► "greeting"        → [greeting_node]  → END
    ├──► "product_inquiry" → [rag_node]        → END
    └──► "high_intent"     → [lead_collection] → END
              ↑                      │
              └──────────────────────┘
              (loops back if mid-collection)
```

The `lead_collection` node checks `awaiting_lead_field` to know which piece of info to ask for next. The mock tool fires **only** when all three fields are non-null — making premature tool execution impossible.

### RAG Pipeline

The knowledge base (`knowledge_base.md`) is:
1. Loaded and chunked by markdown sections
2. Embedded using `sentence-transformers/all-MiniLM-L6-v2` (runs locally, free)
3. Stored in a FAISS vector index
4. Retrieved via semantic similarity on user queries
5. Injected as context into the LLM prompt

---

## 📱 WhatsApp Deployment via Webhooks

To deploy this agent on WhatsApp, use the **WhatsApp Business API** (via Meta or Twilio):

### Architecture

```
WhatsApp User
    │  (sends message)
    ▼
Meta WhatsApp Business API
    │  (HTTP POST Webhook)
    ▼
Your FastAPI Server  ──► AutoStream LangGraph Agent
    │                         │
    │  (AI Response)          │  (state stored in Redis)
    ▼                         │
Meta API (send message) ◄────┘
    │
    ▼
WhatsApp User (receives reply)
```

### Step-by-Step Integration

**1. Set up a FastAPI webhook server:**
```python
from fastapi import FastAPI, Request
from agent import build_graph, get_initial_state
import redis, json

app = FastAPI()
graph = build_graph()
r = redis.Redis()  # Store per-user state

@app.post("/webhook")
async def whatsapp_webhook(req: Request):
    data = await req.json()
    phone = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    text  = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    
    # Load user state from Redis
    state_json = r.get(f"state:{phone}")
    state = json.loads(state_json) if state_json else get_initial_state()
    
    # Add user message and invoke graph
    from langchain_core.messages import HumanMessage
    state["messages"].append(HumanMessage(content=text))
    result = graph.invoke(state)
    
    # Save updated state
    r.setex(f"state:{phone}", 3600, json.dumps(result, default=str))
    
    # Send reply back via WhatsApp API
    reply = result["messages"][-1].content
    send_whatsapp_message(phone, reply)
    return {"status": "ok"}
```

**2. Register your webhook URL** in the Meta Developer Console under WhatsApp → Configuration → Webhook URL.

**3. Handle verification:** Meta sends a GET request with a `hub.challenge` token — your server must echo it back.

**4. Use Twilio as an alternative** (simpler setup):
```python
from twilio.twiml.messaging_response import MessagingResponse

@app.post("/twilio-webhook")
async def twilio_webhook(Body: str = Form(...), From: str = Form(...)):
    # Same logic as above
    ...
    resp = MessagingResponse()
    resp.message(reply)
    return Response(content=str(resp), media_type="application/xml")
```

**Key considerations for production:**
- Store conversation state in **Redis** (per phone number, TTL of ~1 hour)
- Use **ngrok** during development to expose your local server
- Handle **message deduplication** (WhatsApp may send duplicate webhooks)
- Add **rate limiting** to prevent abuse

---

## 📁 Project structure

```
AutoStream/
├── .venv/               # optional: local virtualenv (gitignored; create at repo root)
├── .gitignore
├── run_api.py            # local: `python run_api.py` — FastAPI from repo root
├── render.yaml           # optional: Render Blueprint (API + static)
├── .env                 # API keys (gitignored) — copy from .env.example if present
├── backend/             # Python: agent, RAG, API, CLI
│   ├── main_api.py      # FastAPI app (uvicorn backend.main_api:app)
│   ├── cli.py           # Terminal chat loop; run via python -m backend
│   ├── agent.py
│   ├── intent_classifier.py
│   ├── rag_pipeline.py
│   ├── tools.py
│   ├── knowledge_base.md
│   ├── requirements.txt # pip install -r backend/requirements.txt
│   └── leads_log.json   # auto-created (gitignored by default)
└── frontend/            # Vite + React UI
    ├── src/
    └── package.json
```

---

## 🧪 Quick module checks (from project root)

```bash
# RAG (loads knowledge base, may build FAISS on first run)
python -m backend.rag_pipeline

# Lead capture (writes a test row; check backend/leads_log.json)
python -m backend.tools
```

---

## 📊 Evaluation Criteria Addressed

| Criterion | Implementation |
|-----------|---------------|
| Agent reasoning & intent detection | LLM-based classifier + keyword fallback |
| Correct RAG usage | FAISS + sentence-transformers, context injected in prompt |
| Clean state management | TypedDict state passed through LangGraph nodes |
| Proper tool calling | Tool fires only when all 3 lead fields are collected |
| Code clarity | Modular files, docstrings, type hints throughout |
| Real-world deployability | WhatsApp webhook architecture documented above |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | LangGraph 0.2+ |
| LLM | Gemini 1.5 Flash |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS |
| Language | Python 3.9+ |
| State | LangGraph TypedDict |

---

*Built for ServiceHive Inflx — Social-to-Lead Agentic Workflow Assignment*
