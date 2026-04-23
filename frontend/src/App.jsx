import { useCallback, useEffect, useMemo, useState } from "react";

const SESSION_KEY = "autostream_session_id";
const defaultDirect = "http://127.0.0.1:8000";
/** In dev, Vite proxies /api/* → FastAPI (no CORS). Set VITE_API_BASE to call the API directly. */
const useViteProxy = import.meta.env.DEV && !import.meta.env.VITE_API_BASE;

/** Normalized public API base (https://). In production, VITE_API_BASE must be the FastAPI host, not the static site. */
function normalizeApiBase() {
  const raw = import.meta.env.VITE_API_BASE;
  if (raw == null || String(raw).trim() === "") return null;
  const t = String(raw).trim().replace(/\/$/, "");
  if (t.startsWith("http://") || t.startsWith("https://")) return t;
  return `https://${t}`;
}

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (useViteProxy) return `/api${p}`;
  const base = normalizeApiBase() || defaultDirect;
  return `${base}${p}`;
}

function apiLabel() {
  if (useViteProxy) return "Vite /api/ → 127.0.0.1:8000";
  const nb = normalizeApiBase();
  if (nb) return nb;
  return defaultDirect;
}

function useDeploymentConfigWarning() {
  const [text, setText] = useState(null);
  useEffect(() => {
    if (import.meta.env.DEV) return;
    const nb = normalizeApiBase();
    if (!nb) {
      setText(
        "Production build: VITE_API_BASE is missing. On Render, set it on the static service to your API URL (e.g. https://your-api.onrender.com), then rebuild."
      );
      return;
    }
    try {
      if (new URL(nb).origin === window.location.origin) {
        setText(
          "VITE_API_BASE points to this static site. It must be your separate API URL (e.g. https://your-backend.onrender.com). Update the env on Render and redeploy the static site."
        );
      }
    } catch {
      /* invalid URL */
    }
  }, []);
  return text;
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
  greeting: { label: "Casual", prefix: "Intent" },
  product_inquiry: { label: "Inquiring", prefix: "Intent" },
  high_intent: { label: "High Intent", prefix: "Intent" },
};

function intentBadge(intent) {
  const m = INTENT_META[intent] || { label: intent || "-", prefix: "Intent" };
  return `${m.prefix}: ${m.label}`;
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
      let detail = `${r.status} ${r.statusText}`;
      try {
        const j = await r.json();
        if (j.detail != null) {
          detail =
            typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((x) => x.msg || JSON.stringify(x)).join("; ") : JSON.stringify(j.detail);
        }
      } catch {
        /* ignore */
      }
      const err = new Error(detail);
      err.status = r.status;
      throw err;
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
      const m = e instanceof Error ? e.message : "";
      const status = e && typeof e === "object" && "status" in e ? e.status : undefined;
      const is404 = m.includes("404") || m === "Not Found";
      const is500 = status === 500 || m.startsWith("500 ");
      setError(m || "Request failed");
      setMessages((m_) => [
        ...m_,
        {
          role: "assistant",
          text: is404
            ? "Could not reach the API (404). If you are on Render, VITE_API_BASE on the static site must be your API’s https://… URL (not this page’s URL). Rebuild the static site after changing it."
            : is500
              ? `Server error (500). Details: ${m.slice(0, 800)}${m.length > 800 ? "…" : ""}`
              : "Something went wrong. In local dev, ensure the API is on port 8000. On Render, set GEMINI_API_KEY only on the API service and check the API logs.",
        },
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
  const deployWarning = useDeploymentConfigWarning();

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">AS</span>
          <div>
            <h1>AutoStream Agent</h1>
            <p className="subtitle">LangGraph · Gemini · RAG</p>
          </div>
        </div>
        <div className="header-right">
          <span
            className={`health ${health?.ok && health?.keyOk !== false ? "ok" : health?.ok && health?.keyOk === false ? "warn" : "down"}`}
            title="GET /health"
          >
            {!health?.ok
              ? "API …"
              : health?.keyOk === false
                ? "No Gemini key on API"
                : "API online"}
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

      {deployWarning && <div className="banner config">{deployWarning}</div>}

      {health?.ok && health?.keyOk === false && (
        <div className="banner config">
          The API is reachable but <strong>GEMINI_API_KEY</strong> (or <strong>GOOGLE_API_KEY</strong>) is not set on the
          <strong> API web service</strong> in Render. Add it in Environment, save, and redeploy the API. Do not put the key on the static
          site.
        </div>
      )}

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
        .then(async (r) => {
          if (cancelled) return;
          let keyOk = true;
          try {
            const j = await r.json();
            if (j && typeof j.gemini_key_configured === "boolean") keyOk = j.gemini_key_configured;
          } catch {
            /* old API without field */
          }
          setHealth({ ok: r.ok, keyOk });
        })
        .catch(() => {
          if (!cancelled) setHealth({ ok: false, keyOk: undefined });
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
