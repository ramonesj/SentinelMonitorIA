import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "./api";

function messageId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function welcomeMessage() {
  return {
    id: "welcome",
    role: "assistant",
    content: "Hola. Puedo consultar las alertas recientes de tu organización y resumir su estado operativo. Las acciones automáticas están deshabilitadas.",
    provider: "rules",
    suggestions: ["¿Cuántas alertas abiertas hay?", "Resume las alertas críticas", "¿Qué puedes hacer?"]
  };
}

function ChatWidget({ session }) {
  const accessToken = session?.access_token;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState(() => [welcomeMessage()]);
  const [conversationId, setConversationId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);

  useEffect(() => {
    setMessages([welcomeMessage()]);
    setConversationId("");
    setDraft("");
    setError("");
  }, [accessToken]);

  useEffect(() => {
    if (open && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, open, sending]);

  const sendMessage = async (rawMessage) => {
    const message = rawMessage.trim();
    if (!message || !accessToken || sending) return;

    setMessages((current) => [...current, { id: messageId(), role: "user", content: message }]);
    setDraft("");
    setError("");
    setSending(true);

    try {
      const response = await sendChatMessage(accessToken, {
        message,
        ...(conversationId ? { conversation_id: conversationId } : {})
      });
      setConversationId(response.conversation_id || "");
      setMessages((current) => [...current, {
        id: messageId(),
        role: "assistant",
        content: response.message || "No recibí una respuesta del proveedor de chat.",
        provider: response.provider || "rules",
        suggestions: Array.isArray(response.suggestions) ? response.suggestions : [],
        sources: Array.isArray(response.sources) ? response.sources : [],
        contextSummary: response.context_summary || null
      }]);
    } catch (requestError) {
      setError(requestError.message || "No se pudo consultar el chatbot");
    } finally {
      setSending(false);
    }
  };

  const submit = (event) => {
    event.preventDefault();
    sendMessage(draft);
  };

  const reset = () => {
    setMessages([welcomeMessage()]);
    setConversationId("");
    setDraft("");
    setError("");
  };

  if (!accessToken) return null;

  return (
    <aside className={`chat-widget${open ? " chat-widget-open" : ""}`} aria-label="Asistente operativo">
      {open && <section className="chat-panel" aria-labelledby="chat-heading">
        <header className="chat-panel-header">
          <div>
            <span className="chat-kicker">LOCAL INTELLIGENCE</span>
            <h2 id="chat-heading">Operations assistant</h2>
            <p>Contexto de alertas, sin acciones automáticas</p>
          </div>
          <div className="chat-panel-actions">
            <button type="button" className="chat-reset" onClick={reset} title="Iniciar una conversación nueva">↻</button>
            <button type="button" className="chat-close" onClick={() => setOpen(false)} aria-label="Cerrar asistente">×</button>
          </div>
        </header>
        <div className="chat-messages" ref={messagesRef} aria-live="polite">
          {messages.map((message, index) => <div className={`chat-message-row chat-message-${message.role}`} key={message.id}>
            <div className="chat-message-bubble">
              <span className="chat-message-role">{message.role === "user" ? "Tú" : "Asistente"}</span>
              <p>{message.content}</p>
              {message.role === "assistant" && message.contextSummary && <small className="chat-context-note">{message.contextSummary.alerts_considered || 0} alertas consultadas · proveedor {message.provider}</small>}
            </div>
            {message.role === "assistant" && index === messages.length - 1 && !sending && message.suggestions?.length > 0 && <div className="chat-suggestions">
              {message.suggestions.slice(0, 3).map((suggestion) => <button type="button" key={suggestion} onClick={() => sendMessage(suggestion)}>{suggestion}</button>)}
            </div>}
          </div>)}
          {sending && <div className="chat-message-row chat-message-assistant"><div className="chat-message-bubble chat-message-thinking"><span className="chat-message-role">Asistente</span><p><span className="chat-thinking-dot" /> Consultando contexto operativo...</p></div></div>}
        </div>
        {error && <div className="chat-error" role="alert">{error}</div>}
        <form className="chat-form" onSubmit={submit}>
          <input value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={2000} placeholder="Pregunta por el estado operativo..." aria-label="Mensaje para el asistente" disabled={sending} />
          <button type="submit" disabled={sending || !draft.trim()} aria-label="Enviar mensaje">↗</button>
        </form>
        <footer className="chat-panel-footer">Modo local · reglas · lectura segura</footer>
      </section>}
      <button type="button" className="chat-launcher" onClick={() => setOpen((current) => !current)} aria-expanded={open} aria-controls="chat-heading">
        <span className="chat-launcher-icon">{open ? "×" : "✦"}</span>
        <span className="chat-launcher-label">{open ? "Cerrar" : "Ask Sentinel"}</span>
      </button>
    </aside>
  );
}

export default ChatWidget;
