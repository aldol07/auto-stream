import { useCallback, useEffect, useMemo, useState } from "react";

const SESSION_KEY = "autostream_session_id";
const defaultDirect = "http://127.0.0.1:8000";
/** In dev, Vite proxies /api/* → FastAPI (no CORS). Set VITE_API_BASE to call the API directly. */
const useViteProxy = import.meta.env.DEV && !import.meta.env.VITE_API_BASE;

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (useViteProxy) return `/api${p}`;
  return `${(import.meta.env.VITE_API_BASE || defaultDirect).replace(/\/$/, "")}${p}`;
}

function apiLabel() {
  if (useViteProxy) return "Vite /api/ → 127.0.0.1:8000";
  return import.meta.env.VITE_API_BASE || defaultDirect;
}

function getOrCreateSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

const INTENT_META = {
  greeting: { label: "Casual", emoji: "💬" },
  product_inquiry: { label: "Inquiring", emoji: "🔍" },
  high_intent: { label: "High Intent", emoji: "🔥" },
};

function intentBadge(intent) {
  const m = INTENT_META[intent] || { label: intent || "—", emoji: "💬" };
  return `${m.emoji} ${m.label}`;
}

export default function App() {
  const [tab, setTab] = useState("chat");
  const [sessionId, setSessionId] = useState(() => getOrCreateSessionId());
  const [messages, setMessages] = useState(() => [
    {
      role: "assistant",
      text:
        "Hi! I'm the AutoStream AI assistant. Ask about plans, features, or pricing — or say you're ready to get started.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [intent, setIntent] = useState("greeting");
  const [leads, setLeads] = useState([]);

  const canSend = input.trim().length > 0 && !sending;

  const postJson = useCallback(async (path, body) => {
    const r = await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      let detail = r.statusText;
      try {
        const j = await r.json();
        if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return r.json();
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;
    setError(null);
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setSending(true);
    try {
      const data = await postJson("/chat", { session_id: sessionId, message: text });
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_KEY, data.session_id);
      }
      setIntent(data.intent || "greeting");
      setMessages((m) => [...m, { role: "assistant", text: data.reply || "" }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Something went wrong. Is the API running on port 8000?" },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, postJson, sessionId]);

  const loadLeads = useCallback(async () => {
    try {
      const r = await fetch(apiUrl("/leads"));
      if (!r.ok) throw new Error(r.statusText);
      const data = await r.json();
      setLeads(Array.isArray(data) ? data : []);
    } catch {
      setLeads([]);
    }
  }, []);

  useEffect(() => {
    if (tab !== "leads") return undefined;
    loadLeads();
    const t = setInterval(loadLeads, 4000);
    return () => clearInterval(t);
  }, [tab, loadLeads]);

  const health = useApiHealth();
  const intentDisplay = useMemo(() => intentBadge(intent), [intent]);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">🎬</span>
          <div>
            <h1>AutoStream Agent</h1>
            <p className="subtitle">LangGraph · Gemini · RAG</p>
          </div>
        </div>
        <div className="header-right">
          <span className={`health ${health?.ok ? "ok" : "down"}`} title="GET /health">
            {health?.ok ? "API online" : "API …"}
          </span>
          <span className="intent-badge" title="Last classified intent">
            {intentDisplay}
          </span>
        </div>
      </header>

      <nav className="tabs">
        <button type="button" className={tab === "chat" ? "active" : ""} onClick={() => setTab("chat")}>
          Chat
        </button>
        <button type="button" className={tab === "leads" ? "active" : ""} onClick={() => setTab("leads")}>
          Leads
        </button>
        <button type="button" className={tab === "debug" ? "active" : ""} onClick={() => setTab("debug")}>
          Intent
        </button>
      </nav>

      {error && <div className="banner error">{error}</div>}

      {tab === "chat" && (
        <section className="panel chat-panel">
          <div className="messages">
            {messages.map((msg, i) => (
              <div key={i} className={`bubble ${msg.role}`}>
                {msg.text}
              </div>
            ))}
            {sending && <div className="bubble assistant dim">…</div>}
          </div>
          <div className="composer">
            <input
              type="text"
              placeholder="Message AutoStream…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
              disabled={sending}
            />
            <button type="button" disabled={!canSend} onClick={sendMessage}>
              Send
            </button>
            <button
              type="button"
              className="secondary"
              onClick={async () => {
                await postJson("/reset", { session_id: sessionId });
                setMessages([
                  {
                    role: "assistant",
                    text: "Session cleared. How can I help you with AutoStream today?",
                  },
                ]);
                setIntent("greeting");
              }}
            >
              Reset
            </button>
          </div>
        </section>
      )}

      {tab === "leads" && (
        <section className="panel">
          <div className="panel-head">
            <h2>Captured leads</h2>
            <button type="button" className="small" onClick={loadLeads}>
              Refresh
            </button>
          </div>
          <div className="table-wrap">
            <table className="leads-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Platform</th>
                  <th>Captured</th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty">
                      No leads yet. Complete a high-intent flow in Chat.
                    </td>
                  </tr>
                )}
                {leads.map((row) => (
                  <tr key={row.lead_id || row.email + row.captured_at}>
                    <td>{row.name}</td>
                    <td>{row.email}</td>
                    <td>{row.platform}</td>
                    <td className="mono">{row.captured_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "debug" && (
        <section className="panel debug-panel">
          <h2>Intent (live)</h2>
          <p className="big-intent">{intentDisplay}</p>
          <p className="mono small">Raw: {intent}</p>
          <p className="hint">Updates after each assistant reply in Chat.</p>
        </section>
      )}

      <footer className="footer">
        <span className="mono">session: {sessionId.slice(0, 8)}…</span>
        <span> · </span>
        <span>API: {apiLabel()}</span>
      </footer>
    </div>
  );
}

function useApiHealth() {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const check = () => {
      fetch(apiUrl("/health"))
        .then((r) => {
          if (!cancelled) setHealth({ ok: r.ok });
        })
        .catch(() => {
          if (!cancelled) setHealth({ ok: false });
        });
    };
    check();
    const t = setInterval(check, 10000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);
  return health;
}
