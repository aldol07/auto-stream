# AutoStream Agent

Live app: [https://auto-stream-itfv.onrender.com](https://auto-stream-itfv.onrender.com)

## 1) How to run locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Gemini API key

### Setup
```bash
cd AutoStream
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

Create `.env` in project root:
```env
GEMINI_API_KEY=your_key_here
```

Note: If models such as GPT-4o-mini, Gemini 1.5 Flash, or Claude 3 Haiku are not freely available in your account, paste your own valid API key and then test.

### Run backend + frontend (two terminals)

Terminal A (API):
```bash
python backend/render_entry.py
```

Terminal B (UI):
```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://127.0.0.1:5173`).

### Optional CLI mode
```bash
python -m backend
```

## 1.1) Brief deployment instructions (Render)

1. Push this repo to GitHub.
2. In Render, create two services from the same repo:
   - Web Service (API): start command `python backend/render_entry.py`
   - Static Site (frontend): build `cd frontend && npm install && npm run build`, publish `frontend/dist`
3. Set environment variables:
   - API service: `GEMINI_API_KEY`, `CORS_ORIGINS=https://auto-stream-itfv.onrender.com`
   - Static service: `VITE_API_BASE=<your_api_service_url>`
4. Deploy API first, then deploy the static site.
5. Open the live app URL.

## 2) Architecture explanation (~200 words)

I used LangGraph because this workflow is stateful and rule-driven, not just a single prompt-response loop. The agent has clear stages: intent classification, greeting/product response, lead collection, and tool execution. LangGraph fits this well because each stage is a node, transitions are explicit, and conditional routing is deterministic. That makes behavior easy to debug and prevents accidental tool calls.

I did not choose AutoGen because this project does not need multiple autonomous agents negotiating tasks. It needs a single reliable assistant with strict control over when it asks for lead fields and when it triggers the capture tool.

State is managed through a typed dictionary (`AgentState`) that is passed through graph execution. It contains conversation messages, current intent, lead fields (`lead_name`, `lead_email`, `lead_platform`), and control flags (`awaiting_lead_field`, `lead_captured`). In the API layer, state is stored per session id in memory (`_sessions[session_id]`). This keeps multi-turn context across HTTP requests. For local and demo usage this is sufficient; for production, the same state structure can move to Redis so sessions survive restarts and can scale across multiple instances.

RAG is implemented with local embeddings and FAISS. Product questions retrieve relevant KB chunks and inject them into the model prompt before response generation.

## 3) WhatsApp deployment via webhooks

To integrate with WhatsApp, deploy the FastAPI app publicly and add a webhook endpoint (for Meta WhatsApp Cloud API or Twilio WhatsApp). Incoming webhook messages include sender phone and text. Use sender phone as the session key, load existing state, append the new user message, run `graph.invoke(state)`, save updated state, then send the assistant reply back through the WhatsApp send-message API.

Recommended production flow:
- Webhook endpoint: `POST /webhook` for inbound messages
- Verification endpoint: `GET /webhook` for Meta challenge validation
- Persistent state store: Redis (keyed by phone number, with TTL)
- Idempotency: deduplicate repeated webhook deliveries
- Reliability: queue outbound sends + retries
- Security: verify webhook signatures and keep API keys in environment variables

This preserves the same agent logic while changing only the transport layer (terminal/web UI -> WhatsApp).
