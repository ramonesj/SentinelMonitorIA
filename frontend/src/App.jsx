import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import kiroLogo from "../../Imagenes/cai.png";
import codeFacilitoLogo from "../../Imagenes/bu.png";
import peruFlag from "../../Imagenes/peru.png";
import venezuelaFlag from "../../Imagenes/bandeira-venezuela-flag-0.png";
import { API_BASE_URL, acknowledgeAlert, connectAlertsWebSocket, fetchAlerts, fetchDashboardData } from "./api";
import ChatWidget from "./ChatWidget";
import { clearSession, createApiKey, listApiKeys, listOrganizationMembers, addOrganizationMember, updateOrganizationMember, removeOrganizationMember, createOrganizationInvitation, listOrganizationInvitations, revokeOrganizationInvitation, acceptOrganizationInvitation, login, logout, readSession, register, restoreSession, revokeApiKey, rotateApiKey } from "./auth";

const REFRESH_INTERVAL_MS = 30000;
const ALERT_POLL_INTERVAL_MS = 15000;
const ALERT_RECONNECT_DELAY_MS = 5000;
const THEME_STORAGE_KEY = "sentinelmonitoria.theme";

function getInitialTheme() {
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "light" || storedTheme === "dark") return storedTheme;
  } catch {
    // Fall back to the system preference when storage is unavailable.
  }
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

const serviceConfig = [
  { key: "database", label: "PostgreSQL", code: "PG", description: "Data layer" },
  { key: "redis", label: "Redis cache", code: "RD", description: "Fast storage" },
  { key: "telemetry_service", label: "Telemetry engine", code: "TM", description: "Processing" }
];

const queueLabels = {
  telemetry: "Telemetry",
  metrics: "Metrics",
  logs: "Logs",
  events: "Events",
  ai_analysis: "AI analysis",
  notifications: "Notifications",
  alerts: "Alerts",
  dead_letter: "Dead letter"
};

const teamMembers = [
  { flag: peruFlag, country: "Perú", name: "Jeffersson Pretell Velasquez", email: "jpretelll66@gmail.com" },
  { flag: peruFlag, country: "Perú", name: "Fernanda Flórez Hereña", email: "fernandaflorezherena@gmail.com" },
  { flag: venezuelaFlag, country: "Venezuela", name: "Jose Jose Ramones Moreno", email: "ramonesj@gmail.com" }
];

function formatNumber(value) {
  return new Intl.NumberFormat("es-ES").format(Number(value) || 0);
}

function formatPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function formatTime(date) {
  if (!date) return "--:--:--";
  return date.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDate(date = new Date()) {
  return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(date).toUpperCase();
}

function statusLabel(status) {
  if (status === "healthy") return "Operational";
  if (status === "degraded") return "Degraded";
  if (status === "unhealthy") return "Attention needed";
  return "Waiting for signal";
}

function StatusDot({ status }) {
  return <span className={`status-dot status-${status || "unknown"}`} aria-hidden="true" />;
}

function NavIcon({ children }) {
  return <span className="nav-icon" aria-hidden="true">{children}</span>;
}

function KpiCard({ label, value, detail, accent, marker }) {
  return (
    <article className={`kpi-card kpi-${accent}`}>
      <div className="kpi-topline"><span className="kpi-label">{label}</span><span className="kpi-marker">{marker}</span></div>
      <strong className="kpi-value">{value}</strong>
      <span className="kpi-detail">{detail}</span>
    </article>
  );
}

function sortAlerts(alerts) {
  return [...alerts].sort((left, right) => {
    const rightTime = Date.parse(right.created_at || "") || 0;
    const leftTime = Date.parse(left.created_at || "") || 0;
    return rightTime - leftTime;
  });
}

function mergeAlerts(current, incoming) {
  const next = new Map(current.map((alert) => [alert.id, alert]));
  const items = Array.isArray(incoming) ? incoming : [incoming];
  items.filter((alert) => alert?.id).forEach((alert) => {
    next.set(alert.id, { ...next.get(alert.id), ...alert });
  });
  return sortAlerts([...next.values()]);
}

function alertSeverity(alert) {
  return String(alert?.severity || "info").toLowerCase();
}

function alertStatus(alert) {
  return String(alert?.status || "open").toLowerCase();
}

function formatAlertDate(value) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" });
}

function useAlertStream(accessToken) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [lastEventAt, setLastEventAt] = useState(null);
  const [acknowledgingId, setAcknowledgingId] = useState("");

  const loadAlerts = useCallback(async () => {
    if (!accessToken) return [];
    try {
      const nextAlerts = await fetchAlerts(accessToken);
      setAlerts(sortAlerts(nextAlerts));
      setError("");
      return nextAlerts;
    } catch (requestError) {
      setError(requestError.message || "No se pudieron cargar las alertas");
      throw requestError;
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    let active = true;
    let socket = null;
    let pollTimer = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;

    const stopPolling = () => {
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const poll = async () => {
      try {
        await loadAlerts();
        if (active) setConnectionStatus((current) => current === "live" ? current : "polling");
      } catch {
        if (active) setConnectionStatus("polling");
      }
    };

    const startPolling = () => {
      if (pollTimer !== null) return;
      poll();
      pollTimer = window.setInterval(poll, ALERT_POLL_INTERVAL_MS);
    };

    const scheduleReconnect = () => {
      if (!active || reconnectTimer !== null) return;
      const delay = Math.min(30000, ALERT_RECONNECT_DELAY_MS * (2 ** Math.min(reconnectAttempts, 3)));
      reconnectAttempts += 1;
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        openSocket();
      }, delay);
    };

    const openSocket = () => {
      if (!active) return;
      try {
        socket = connectAlertsWebSocket(accessToken);
      } catch (connectionError) {
        setError(connectionError.message || "No se pudo abrir el canal de alertas");
        startPolling();
        scheduleReconnect();
        return;
      }

      if (!socket) {
        setConnectionStatus("polling");
        startPolling();
        return;
      }

      setConnectionStatus(reconnectAttempts ? "reconnecting" : "connecting");
      socket.onopen = () => {
        if (!active) return;
        reconnectAttempts = 0;
        stopPolling();
        setConnectionStatus("live");
        setError("");
      };
      socket.onmessage = (event) => {
        if (!active) return;
        try {
          const alert = JSON.parse(event.data);
          if (alert?.id) {
            setAlerts((current) => mergeAlerts(current, alert));
            setLastEventAt(new Date());
            setError("");
          }
        } catch {
          setError("El canal de alertas devolvió un mensaje no válido");
        }
      };
      socket.onerror = () => {
        if (active) setError("El WebSocket de alertas no está disponible; usando polling");
      };
      socket.onclose = () => {
        socket = null;
        if (!active) return;
        setConnectionStatus("polling");
        startPolling();
        scheduleReconnect();
      };
    };

    setAlerts([]);
    setLoading(true);
    setError("");
    setLastEventAt(null);
    setConnectionStatus("connecting");
    loadAlerts().catch(() => undefined).finally(() => {
      if (active) openSocket();
    });

    return () => {
      active = false;
      stopPolling();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, [accessToken, loadAlerts]);

  const acknowledge = useCallback(async (alertId) => {
    if (!accessToken) return null;
    setAcknowledgingId(alertId);
    try {
      const response = await acknowledgeAlert(accessToken, alertId);
      const updatedAlert = response.alert || response;
      if (updatedAlert?.id) setAlerts((current) => mergeAlerts(current, updatedAlert));
      return updatedAlert;
    } catch (requestError) {
      setError(requestError.message || "No se pudo reconocer la alerta");
      return null;
    } finally {
      setAcknowledgingId("");
    }
  }, [accessToken]);

  return { alerts, loading, error, connectionStatus, lastEventAt, acknowledgingId, acknowledge };
}

function alertConnectionLabel(status) {
  if (status === "live") return "WebSocket live";
  if (status === "polling") return "Polling fallback";
  if (status === "reconnecting") return "Reconnecting";
  return "Connecting";
}

function AlertPanel({ alerts, loading, error, connectionStatus, lastEventAt, acknowledgingId, onAcknowledge }) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    const matchesStatus = statusFilter === "all" || alertStatus(alert) === statusFilter;
    const matchesSeverity = severityFilter === "all" || alertSeverity(alert) === severityFilter;
    return matchesStatus && matchesSeverity;
  }), [alerts, severityFilter, statusFilter]);

  return (
    <section className="alerts-panel" id="alerts" aria-labelledby="alerts-heading">
      <div className="alerts-heading">
        <div>
          <p className="section-kicker">INTELLIGENCE STREAM</p>
          <h2 id="alerts-heading">Alerts &amp; AI analysis</h2>
          <p>Señales detectadas por reglas deterministas, explicaciones opcionales y recomendaciones de sólo lectura.</p>
        </div>
        <div className="alerts-status-stack">
          <span className={`alert-stream-status alert-stream-${connectionStatus}`}><span className="alert-stream-dot" />{alertConnectionLabel(connectionStatus)}</span>
          <small>{lastEventAt ? `Último evento ${formatAlertDate(lastEventAt)}` : `${alerts.length} registros cargados`}</small>
        </div>
      </div>
      {error && <div className="alerts-error" role="alert"><strong>Alert stream</strong><span>{error}</span></div>}
      <div className="alerts-toolbar">
        <div className="alerts-count"><strong>{filteredAlerts.length}</strong><span>alertas visibles</span></div>
        <div className="alert-filters">
          <label>Estado<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">Todos</option><option value="open">Abiertas</option><option value="acknowledged">Reconocidas</option><option value="resolved">Resueltas</option></select></label>
          <label>Severidad<select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}><option value="all">Todas</option><option value="critical">Crítica</option><option value="high">Alta</option><option value="medium">Media</option><option value="low">Baja</option><option value="info">Info</option></select></label>
        </div>
      </div>
      {loading ? <div className="alert-empty"><span className="loader" /> Cargando alertas y contexto IA...</div> : filteredAlerts.length ? <div className="alert-list">
        {filteredAlerts.map((alert) => {
          const severity = alertSeverity(alert);
          const status = alertStatus(alert);
          const payload = alert.payload && typeof alert.payload === "object" ? alert.payload : {};
          const findings = Array.isArray(payload.findings) ? payload.findings : [];
          const recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : findings.map((finding) => finding.recommendation).filter(Boolean);
          return <article className={`alert-card alert-card-${severity}`} key={alert.id}>
            <div className="alert-card-content">
              <div className="alert-card-topline"><span className={`alert-severity-badge alert-severity-${severity}`}>{severity}</span><span className={`alert-status-badge alert-status-${status}`}>{status}</span><span className="alert-rule">{alert.rule_id || alert.source || "intelligence"}</span><time>{formatAlertDate(alert.created_at)}</time></div>
              <h3>{alert.title || "Operational alert"}</h3>
              <div className="alert-explanation"><span className="alert-subheading">AI EXPLANATION / RULE CONTEXT</span><p>{alert.description || "No hay una explicación disponible para esta alerta."}</p></div>
              {findings.length > 0 && <div className="alert-findings"><span className="alert-subheading">DETECTED SIGNALS</span>{findings.slice(0, 3).map((finding, index) => { const evidence = finding.evidence || {}; const evidenceText = evidence.metric ? `${evidence.metric}: ${evidence.value}${evidence.unit || ""}` : evidence.service || evidence.component || evidence.source || "Evidence recorded"; return <div className="alert-finding" key={`${alert.id}-finding-${index}`}><div><strong>{finding.title || finding.rule_id || "Signal"}</strong><span>{finding.description}</span></div><small>{evidenceText}</small></div>; })}</div>}
              {recommendations.length > 0 && <div className="alert-recommendations"><span className="alert-subheading">SAFE NEXT STEPS</span><ul>{recommendations.slice(0, 4).map((recommendation, index) => <li key={`${alert.id}-recommendation-${index}`}>{recommendation}</li>)}</ul></div>}
              <div className="alert-meta"><span>Agent: {payload.agent_id || "--"}</span><span>Batch: {payload.batch_id ? String(payload.batch_id).slice(0, 14) : "--"}</span><span>{payload.actions_enabled === false ? "Automated actions disabled" : "Review action policy"}</span></div>
            </div>
            <div className="alert-card-actions">{status === "open" ? <button type="button" className="alert-acknowledge" onClick={() => onAcknowledge(alert.id)} disabled={acknowledgingId === alert.id}>{acknowledgingId === alert.id ? "Updating..." : "Acknowledge"}</button> : <span className="alert-complete">✓ {status === "resolved" ? "Resolved" : "Acknowledged"}</span>}</div>
          </article>;
        })}
      </div> : <div className="alert-empty"><span className="alert-empty-icon">✓</span><strong>No hay alertas para estos filtros</strong><span>El motor IA permanece activo y mostrará nuevas señales por WebSocket o polling.</span></div>}
    </section>
  );
}

function initialsFor(user) {
  const source = user?.full_name || user?.username || "OP";
  return source.split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    full_name: "",
    organization_name: "Sentinel Local",
    organization_slug: "sentinel-local"
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isRegister = mode === "register";

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const session = isRegister
        ? await register({
            email: form.email,
            username: form.username,
            password: form.password,
            full_name: form.full_name || null,
            organization_name: form.organization_name,
            organization_slug: form.organization_slug || form.organization_name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
          })
        : await login({ username: form.username, password: form.password, remember_me: true });
      onAuthenticated(session);
    } catch (requestError) {
      setError(requestError.message || "No fue posible completar la autenticación");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-glow auth-glow-one" />
      <div className="auth-glow auth-glow-two" />
      <div className="auth-layout">
        <section className="auth-intro">
          <a className="brand auth-brand" href="/">
            <span className="brand-mark"><span>S</span></span>
            <span className="brand-copy"><strong>Sentinel<span>Monitor</span></strong><small>Intelligence platform</small></span>
          </a>
          <div className="auth-intro-content">
            <p className="section-kicker">SECURE OPERATIONS</p>
            <h1>See the signal.<br /><em>Lead with clarity.</em></h1>
            <p>Access your observability workspace and keep every critical service within reach.</p>
            <div className="auth-feature-list">
              <span><i /> Live service intelligence</span>
              <span><i /> Telemetry at a glance</span>
              <span><i /> Secure local workspace</span>
            </div>
          </div>
          <span className="auth-version">SENTINELMONITORIA / LOCAL CONTROL PLANE</span>
        </section>

        <section className="auth-card-wrap">
          <div className="auth-card">
            <div className="auth-card-header"><span className="auth-card-kicker">{isRegister ? "CREATE WORKSPACE" : "WELCOME BACK"}</span><h2>{isRegister ? "Start your workspace" : "Sign in to Sentinel"}</h2><p>{isRegister ? "Create an operator account to access your local control plane." : "Enter your credentials to continue to your operations console."}</p></div>
            {error && <div className="auth-error" role="alert"><span className="auth-error-icon">!</span><span>{error}</span></div>}
            <form className="auth-form" onSubmit={submit}>
              {isRegister && <label>Full name<input name="full_name" value={form.full_name} onChange={updateField} placeholder="Your name" autoComplete="name" /></label>}
              <label>Username or email<input name="username" value={form.username} onChange={updateField} placeholder={isRegister ? "operator" : "operator or email"} autoComplete="username" required /></label>
              {isRegister && <label>Email address<input name="email" type="email" value={form.email} onChange={updateField} placeholder="you@company.com" autoComplete="email" required /></label>}
              <label>Password<input name="password" type="password" value={form.password} onChange={updateField} placeholder="Minimum 8 characters" autoComplete={isRegister ? "new-password" : "current-password"} required /></label>
              {isRegister && <div className="auth-form-grid"><label>Organization<input name="organization_name" value={form.organization_name} onChange={updateField} placeholder="Sentinel Local" required /></label><label>Identificador de organización<input name="organization_slug" value={form.organization_slug} onChange={updateField} placeholder="sentinel-local" pattern="[a-z0-9-]+" required /></label></div>}
              {!isRegister && <div className="auth-form-meta"><label className="checkbox-label"><input type="checkbox" defaultChecked /> <span>Keep me signed in</span></label><span className="secure-label">JWT SESSION</span></div>}
              <button className="auth-submit" type="submit" disabled={submitting}>{submitting ? "Authenticating..." : isRegister ? "Create account" : "Access workspace"}<span>→</span></button>
            </form>
            <div className="auth-switch">{isRegister ? "Already have an account?" : "New to SentinelMonitor?"}<button type="button" onClick={() => { setMode(isRegister ? "login" : "register"); setError(""); }}>{isRegister ? "Sign in" : "Create account"}</button></div>
            <small className="auth-disclaimer">Development environment · Access protected by JWT</small>
          </div>
        </section>
      </div>
    </div>
  );
}

function AuthLoading() {
  return <div className="auth-loading"><span className="loader" /><span>Restoring secure session...</span></div>;
}

function IntegrationPanel({ session }) {
  const user = session.user || {};
  const organization = user.organizations?.[0];
  const canManageOrganization = organization?.role === "admin" || organization?.role === "manager";
  const [tokens, setTokens] = useState([]);
  const [form, setForm] = useState({ name: "Local telemetry agent", expiresInDays: "30" });
  const [generatedToken, setGeneratedToken] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const loadTokens = useCallback(async () => {
    setLoading(true);
    try {
      const response = await listApiKeys(session);
      setTokens(response.tokens || []);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "No se pudieron cargar las API keys");
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    loadTokens();
  }, [loadTokens]);

  const submit = async (event) => {
    event.preventDefault();
    if (!organization || !canManageOrganization) return;
    setSubmitting(true);
    setGeneratedToken("");
    setCopied(false);
    setError("");

    try {
      const tokenData = {
        name: form.name,
        organization_id: organization?.id,
        ...(form.expiresInDays ? { expires_in_days: Number(form.expiresInDays) } : {})
      };
      const response = await createApiKey(session, tokenData);
      setGeneratedToken(response.token);
      await loadTokens();
    } catch (requestError) {
      setError(requestError.message || "No se pudo generar la API key");
    } finally {
      setSubmitting(false);
    }
  };

  const copyToken = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(generatedToken);
          setCopied(true);
          return;
        } catch {
          // HTTP pages can expose the API but reject it outside a secure context.
        }
      }

      const textArea = document.createElement("textarea");
      textArea.value = generatedToken;
      textArea.setAttribute("readonly", "");
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.select();
      textArea.setSelectionRange(0, textArea.value.length);
      const copied = document.execCommand("copy");
      document.body.removeChild(textArea);
      if (!copied) throw new Error("Clipboard fallback failed");
      setCopied(true);
    } catch {
      setError("No se pudo copiar automáticamente. Selecciona la key y cópiala manualmente.");
    }
  };

  const handleRevoke = async (tokenId) => {
    if (!window.confirm("¿Revocar esta API key? Los agentes que la usen dejarán de enviar telemetry.")) return;
    try {
      await revokeApiKey(session, tokenId);
      await loadTokens();
    } catch (requestError) {
      setError(requestError.message || "No se pudo revocar la API key");
    }
  };

  const handleRotate = async (token) => {
    if (!window.confirm("¿Rotar esta API key? La key actual se revocará inmediatamente.")) return;
    try {
      const response = await rotateApiKey(session, token.id, { name: `${token.name} (rotated)` });
      setGeneratedToken(response.token);
      setCopied(false);
      await loadTokens();
    } catch (requestError) {
      setError(requestError.message || "No se pudo rotar la API key");
    }
  };

  const endpoint = `${API_BASE_URL}/api/v1/telemetry`;
  const snippet = `curl -X POST ${endpoint} \\\n  -H "Authorization: Bearer ${generatedToken || "API_KEY_GENERADA"}" \\\n  -H "Content-Type: application/json" \\\n  -d '{"metadata":{"agent_id":"agent-local-001","hostname":"localhost","agent_version":"1.0.0"},"metrics":[{"name":"system.cpu.usage","value":42.5}]}'`;

  return (
    <section className="integration-panel" id="integrations">
      <div className="integration-heading">
        <div><p className="section-kicker">SECURE CONNECTIONS</p><h2>Connect a telemetry agent</h2><p>Generate an organization-scoped key and use the endpoint below in Vector, cURL or your own agent.</p></div>
        <span className="integration-endpoint"><span className="pulse-dot" />{endpoint}</span>
      </div>
      {!organization && <div className="integration-warning">Tu usuario no tiene una organización asociada. Registra una organización antes de generar una API key.</div>}
      {organization && !canManageOrganization && <div className="integration-warning">Tu rol actual es <strong>{organization.role}</strong>. Sólo los administradores y managers pueden generar API keys de la organización.</div>}
      {error && <div className="integration-error" role="alert">{error}</div>}
      <div className="integration-grid">
        <form className="integration-form" onSubmit={submit}>
          <label>Key name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Production agent" required /></label>
          <label>Expiration<select value={form.expiresInDays} onChange={(event) => setForm((current) => ({ ...current, expiresInDays: event.target.value }))}><option value="7">7 days</option><option value="30">30 days</option><option value="90">90 days</option><option value="365">365 days</option><option value="">No expiration</option></select></label>
          <div className="integration-org"><span>Organization</span><strong>{organization?.name || "Not configured"}</strong><small>{organization?.slug || "--"}</small></div>
          <button className="integration-submit" type="submit" disabled={submitting || !organization || !canManageOrganization}>{submitting ? "Generating..." : "Generate API key"}<span>→</span></button>
        </form>
        <div className="integration-output">
          {generatedToken ? <div className="generated-key"><div className="generated-key-heading"><strong>Copy this key now</strong><span>Shown once</span></div><div className="key-value">{generatedToken}</div><button type="button" className="copy-key-button" onClick={copyToken}>{copied ? "Copied" : "Copy API key"}</button><pre><code>{snippet}</code></pre></div> : <div className="integration-empty"><span className="integration-empty-icon">↗</span><strong>Your connection details will appear here</strong><span>Keys are displayed only once and are never stored in the browser.</span></div>}
        </div>
      </div>
      <div className="key-list-heading"><span>Active API keys</span><small>{loading ? "Loading..." : `${tokens.length} configured`}</small></div>
      <div className="key-list">{tokens.length ? tokens.map((token) => <div className="key-row" key={token.id}><div><strong>{token.name}</strong><small>{token.expires_at ? `Expires ${new Date(token.expires_at).toLocaleDateString("es-ES")}` : "No expiration"}{token.last_used_at ? ` · Last used ${new Date(token.last_used_at).toLocaleDateString("es-ES")}` : " · Never used"}</small></div><button type="button" onClick={() => handleRotate(token)}>Rotate</button><button type="button" onClick={() => handleRevoke(token.id)}>Revoke</button></div>) : <span className="key-list-empty">No active keys yet.</span>}</div>
    </section>
  );
}

const memberRoleRank = { guest: 10, viewer: 20, member: 30, manager: 40, admin: 50 };

function MembersPanel({ session }) {
  const user = session.user || {};
  const organization = user.organizations?.[0];
  const currentRole = organization?.role || "guest";
  const canManageMembers = currentRole === "admin" || currentRole === "manager";
  const [members, setMembers] = useState([]);
  const [form, setForm] = useState({ email: "", role: currentRole === "manager" ? "member" : "member" });
  const [loading, setLoading] = useState(Boolean(organization));
  const [submitting, setSubmitting] = useState(false);
  const [updatingId, setUpdatingId] = useState("");
  const [error, setError] = useState("");
  const [invitations, setInvitations] = useState([]);
  const [invitationForm, setInvitationForm] = useState({ email: "", role: "member", expires_in_days: 7 });
  const [invitationToken, setInvitationToken] = useState("");
  const invitationTokenRef = useRef(null);
  const [invitationCopyNotice, setInvitationCopyNotice] = useState("");
  const [acceptToken, setAcceptToken] = useState("");
  const [invitationSubmitting, setInvitationSubmitting] = useState(false);

  const loadMembers = useCallback(async () => {
    if (!organization?.id) {
      setMembers([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await listOrganizationMembers(session, organization.id);
      setMembers(response || []);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "No se pudieron cargar los miembros");
    } finally {
      setLoading(false);
    }
  }, [organization?.id, session]);

  const loadInvitations = useCallback(async () => {
    if (!organization?.id) {
      setInvitations([]);
      return;
    }
    try {
      const response = await listOrganizationInvitations(session, organization.id);
      setInvitations(response || []);
    } catch (requestError) {
      setError(requestError.message || "No se pudieron cargar las invitaciones");
    }
  }, [organization?.id, session]);

  useEffect(() => {
    loadMembers();
    loadInvitations();
  }, [loadMembers, loadInvitations]);

  const createInvitation = async (event) => {
    event.preventDefault();
    if (!organization?.id || !canManageMembers) return;
    setInvitationSubmitting(true);
    setInvitationToken("");
    setInvitationCopyNotice("");
    setError("");
    try {
      const invitation = await createOrganizationInvitation(session, organization.id, invitationForm);
      setInvitationToken(invitation.token || "");
      setInvitationForm({ email: "", role: "member", expires_in_days: 7 });
      await loadInvitations();
    } catch (requestError) {
      setError(requestError.message || "No se pudo crear la invitación");
    } finally {
      setInvitationSubmitting(false);
    }
  };

  const revokeInvitation = async (invitation) => {
    if (!window.confirm(`¿Revocar la invitación para ${invitation.email}?`)) return;
    setInvitationSubmitting(true);
    setError("");
    try {
      await revokeOrganizationInvitation(session, organization.id, invitation.id);
      await loadInvitations();
    } catch (requestError) {
      setError(requestError.message || "No se pudo revocar la invitación");
    } finally {
      setInvitationSubmitting(false);
    }
  };

  const acceptInvitation = async (event) => {
    event.preventDefault();
    if (!acceptToken.trim()) return;
    setInvitationSubmitting(true);
    setError("");
    try {
      await acceptOrganizationInvitation(session, acceptToken.trim());
      setAcceptToken("");
      window.alert("Invitación aceptada. La sesión se actualizará ahora.");
      window.location.reload();
    } catch (requestError) {
      setError(requestError.message || "No se pudo aceptar la invitación");
    } finally {
      setInvitationSubmitting(false);
    }
  };

  const copyInvitationToken = async () => {
    setInvitationCopyNotice("");
    setError("");

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(invitationToken);
        setInvitationCopyNotice("Token de invitación copiado.");
        return;
      }
    } catch {
      // HTTP pages can expose the API but reject it outside a secure context.
    }

    const textArea = document.createElement("textarea");
    textArea.value = invitationToken;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    let copied = false;
    try {
      document.body.appendChild(textArea);
      textArea.select();
      textArea.setSelectionRange(0, textArea.value.length);
      copied = document.execCommand?.("copy") === true;
    } catch {
      copied = false;
    } finally {
      if (textArea.parentNode) textArea.parentNode.removeChild(textArea);
    }

    if (copied) {
      setInvitationCopyNotice("Token de invitación copiado.");
      return;
    }

    const tokenInput = invitationTokenRef.current;
    if (tokenInput) {
      tokenInput.focus();
      tokenInput.select();
      tokenInput.setSelectionRange?.(0, tokenInput.value.length);
      setInvitationCopyNotice("El token quedó seleccionado. Presiona Ctrl+C (o ⌘+C) para copiarlo.");
      return;
    }

    setError("No se pudo copiar el token automáticamente. Selecciónalo y cópialo manualmente.");
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!organization?.id || !canManageMembers) return;
    setSubmitting(true);
    setError("");
    try {
      await addOrganizationMember(session, organization.id, form);
      setForm({ email: "", role: "member" });
      await loadMembers();
    } catch (requestError) {
      setError(requestError.message || "No se pudo agregar el miembro");
    } finally {
      setSubmitting(false);
    }
  };

  const updateRole = async (memberId, role) => {
    setUpdatingId(memberId);
    setError("");
    try {
      const updated = await updateOrganizationMember(session, organization.id, memberId, { role });
      setMembers((current) => current.map((member) => member.id === memberId ? updated : member));
    } catch (requestError) {
      setError(requestError.message || "No se pudo actualizar el rol");
    } finally {
      setUpdatingId("");
    }
  };

  const removeMember = async (member) => {
    if (!window.confirm(`¿Retirar a ${member.full_name || member.username} de esta organización?`)) return;
    setUpdatingId(member.id);
    setError("");
    try {
      await removeOrganizationMember(session, organization.id, member.id);
      setMembers((current) => current.filter((item) => item.id !== member.id));
    } catch (requestError) {
      setError(requestError.message || "No se pudo retirar el miembro");
    } finally {
      setUpdatingId("");
    }
  };

  return (
    <section className="members-panel" id="members" aria-labelledby="members-heading">
      <div className="members-heading">
        <div><p className="section-kicker">ORGANIZATION ACCESS</p><h2 id="members-heading">Team members</h2><p>Administra quién puede acceder a esta organización y con qué nivel de responsabilidad.</p></div>
        <span>{loading ? "Loading..." : `${members.length} members`}</span>
      </div>
      {!organization && <div className="integration-warning">Tu usuario no tiene una organización asociada.</div>}
      {error && <div className="integration-error" role="alert">{error}</div>}
      <div className="invitation-section">
        <div className="invitation-grid">
          <form className="invitation-accept-form" onSubmit={acceptInvitation}>
            <label>Aceptar invitación<input value={acceptToken} onChange={(event) => setAcceptToken(event.target.value)} placeholder="Pega aquí tu token de invitación" required /></label>
            <button className="member-add-button" type="submit" disabled={invitationSubmitting}>{invitationSubmitting ? "Processing..." : "Accept invitation"}<span>✓</span></button>
          </form>
          {organization && canManageMembers && <form className="invitation-create-form" onSubmit={createInvitation}>
            <label>Email del invitado<input type="email" value={invitationForm.email} onChange={(event) => setInvitationForm((current) => ({ ...current, email: event.target.value }))} placeholder="operator@example.com" required /></label>
            <label>Rol<select value={invitationForm.role} onChange={(event) => setInvitationForm((current) => ({ ...current, role: event.target.value }))}>{(currentRole === "admin" ? ["admin", "manager", "member", "viewer", "guest"] : ["member", "viewer", "guest"]).map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
            <label>Duración<select value={invitationForm.expires_in_days} onChange={(event) => setInvitationForm((current) => ({ ...current, expires_in_days: Number(event.target.value) }))}><option value={1}>1 día</option><option value={7}>7 días</option><option value={14}>14 días</option><option value={30}>30 días</option></select></label>
            <button className="member-add-button" type="submit" disabled={invitationSubmitting}>{invitationSubmitting ? "Creating..." : "Create invitation"}<span>＋</span></button>
            <small>El token se muestra una sola vez. Envíalo al invitado mediante un canal seguro.</small>
          </form>}
        </div>
        {invitationToken && <div className="invitation-token" role="status"><div><strong>Token creado — cópialo ahora</strong><input ref={invitationTokenRef} className="invitation-token-value" value={invitationToken} readOnly aria-label="Token de invitación" onClick={(event) => event.currentTarget.select()} />{invitationCopyNotice && <small className="invitation-copy-notice">{invitationCopyNotice}</small>}</div><button type="button" onClick={copyInvitationToken}>Copy token</button></div>}
        {organization && <div className="invitation-list"><div className="invitation-list-heading"><span>Invitation history</span><small>{invitations.length} records</small></div>{invitations.length ? invitations.map((invitation) => <div className="invitation-row" key={invitation.id}><div><strong>{invitation.email}</strong><small>{invitation.role} · Expires {new Date(invitation.expires_at).toLocaleDateString("es-ES")}</small></div><span className={`invitation-status invitation-status-${invitation.status}`}>{invitation.status}</span>{canManageMembers && invitation.status === "pending" && <button type="button" onClick={() => revokeInvitation(invitation)} disabled={invitationSubmitting}>Revoke</button>}</div>) : <div className="member-list-empty">No hay invitaciones todavía.</div>}</div>}
      </div>
      {organization && canManageMembers && <form className="member-add-form" onSubmit={submit}>
        <label>Email del usuario<input type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="operator@example.com" required /></label>
        <label>Rol<select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>{(currentRole === "admin" ? ["admin", "manager", "member", "viewer", "guest"] : ["member", "viewer", "guest"]).map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
        <button className="member-add-button" type="submit" disabled={submitting}>{submitting ? "Adding..." : "Add member"}<span>＋</span></button>
        <small>También puedes agregar directamente a un usuario que ya tenga una cuenta.</small>
      </form>}
      <div className="member-list">
        {loading ? <div className="member-list-empty"><span className="loader" /> Loading members...</div> : members.length ? members.map((member) => {
          const canEdit = canManageMembers && member.id !== user.id && (currentRole === "admin" || memberRoleRank[member.role] < memberRoleRank.manager);
          return <div className="member-row" key={member.id}>
            <div className="member-avatar">{initialsFor(member)}</div>
            <div className="member-identity"><strong>{member.full_name || member.username}</strong><span>{member.email}</span><small>{member.username}</small></div>
            <span className={`member-role member-role-${member.role}`}>{member.role}</span>
            {canEdit && <div className="member-actions"><select value={member.role} onChange={(event) => updateRole(member.id, event.target.value)} disabled={updatingId === member.id} aria-label={`Rol de ${member.username}`}>{(currentRole === "admin" ? ["admin", "manager", "member", "viewer", "guest"] : ["member", "viewer", "guest"]).map((role) => <option key={role} value={role}>{role}</option>)}</select><button type="button" onClick={() => removeMember(member)} disabled={updatingId === member.id}>Remove</button></div>}
          </div>;
        }) : <div className="member-list-empty">No hay miembros disponibles.</div>}
      </div>
    </section>
  );
}

function TeamPanel() {
  return (
    <section className="team-panel" aria-labelledby="team-heading">
      <div className="team-heading">
        <div><p className="section-kicker">PROJECT TEAM</p><h2 id="team-heading">Participantes</h2><p>Realizado por nuestro equipo con apoyo de Kiro y Código Facilito.</p></div>
        <span>3 contributors</span>
      </div>
      <div className="team-branding" aria-label="Logos de colaboración">
        <img className="team-brand-logo team-brand-kiro" src={kiroLogo} alt="Hackathon Kiro" />
        <img className="team-brand-logo team-brand-code" src={codeFacilitoLogo} alt="Código Facilito" />
      </div>
      <div className="team-grid">
        {teamMembers.map(({ flag, country, name, email }) => (
          <article className="team-card" key={email}>
            <img className="team-flag" src={flag} alt={`Bandera de ${country}`} />
            <div><strong>{name}</strong><span>{country}</span><a href={`mailto:${email}`}>{email}</a></div>
          </article>
        ))}
      </div>
      <p className="team-updated">Última actualización: 23 de julio de 2026</p>
    </section>
  );
}

function Dashboard({ session, onLogout, theme, onThemeChange }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const user = session.user || {};
  const userInitials = initialsFor(user);
  const { alerts, loading: alertsLoading, error: alertsError, connectionStatus: alertsConnectionStatus, lastEventAt: alertLastEventAt, acknowledgingId, acknowledge } = useAlertStream(session.access_token);
  const openAlertCount = alerts.filter((alert) => alertStatus(alert) === "open").length;
  const highAlertCount = alerts.filter((alert) => ["critical", "high"].includes(alertSeverity(alert)) && alertStatus(alert) === "open").length;

  const loadDashboard = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const nextDashboard = await fetchDashboardData(session.access_token);
      setDashboard(nextDashboard);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "No se pudo conectar con la API");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [session.access_token]);

  useEffect(() => {
    loadDashboard();
    const interval = window.setInterval(() => loadDashboard(true), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadDashboard]);

  const view = useMemo(() => {
    const health = dashboard?.health || {};
    const telemetryStats = dashboard?.telemetryStats?.stats || {};
    const telemetryService = telemetryStats.telemetry_service || {};
    const queueProducer = telemetryStats.queue_producer || {};
    const queueDepths = queueProducer.current_queue_depths || {};
    const healthTelemetry = health.services?.telemetry_service || {};
    return { health, telemetryService: Object.keys(telemetryService).length ? telemetryService : healthTelemetry.stats || {}, queueProducer, queueDepths, metrics: dashboard?.metrics || {} };
  }, [dashboard]);

  const serviceStatuses = view.health.services || {};
  const overallStatus = error ? "unhealthy" : view.health.status || "unknown";
  const telemetryService = view.telemetryService;
  const queueNames = Object.keys(view.queueDepths).length ? Object.keys(view.queueDepths) : Object.keys(queueLabels);
  const healthyServices = serviceConfig.filter(({ key }) => { const service = serviceStatuses[key] || {}; return key === "telemetry_service" ? service.status === "healthy" : service.healthy === true; }).length;
  const healthScore = Math.round((healthyServices / serviceConfig.length) * 100);
  const totalQueueDepth = Object.values(view.queueDepths).reduce((sum, depth) => sum + (Number(depth) || 0), 0);
  const processedMessages = view.metrics.sentinel_queue_messages_processed || 0;
  const sentMessages = view.metrics.sentinel_queue_messages_sent || 0;
  const displayName = user.full_name || user.username || "Operator";

  const validateServiceLinks = async (event) => {
    event.preventDefault();
    await loadDashboard(true);
    document.getElementById("services")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="SentinelMonitorIA inicio"><span className="brand-mark"><span>S</span></span><span className="brand-copy"><strong>Sentinel<span>Monitor</span></strong><small>Intelligence platform</small></span></a>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="main-nav" aria-label="Navegación principal">
          <a className="nav-link active" href="#overview"><NavIcon>OV</NavIcon><span>Overview</span></a><a className="nav-link" href="#services"><NavIcon>SV</NavIcon><span>Services</span></a><a className="nav-link" href="#telemetry"><NavIcon>TP</NavIcon><span>Telemetry</span></a><a className="nav-link nav-alert-link" href="#alerts"><NavIcon>AL</NavIcon><span>Alerts</span>{openAlertCount > 0 && <span className="nav-alert-count">{openAlertCount}</span>}</a><a className="nav-link" href="#integrations"><NavIcon>AK</NavIcon><span>Connections</span></a><a className="nav-link" href="#members"><NavIcon>TM</NavIcon><span>Team members</span></a><a className="nav-link" href={`${API_BASE_URL}/api/v1/docs`} target="_blank" rel="noreferrer"><NavIcon>API</NavIcon><span>API explorer</span><span className="external-mark">↗</span></a>
        </nav>
        <div className="sidebar-section-label sidebar-section-lower">Resources</div>
        <nav className="main-nav"><a className="nav-link" href="#services" onClick={validateServiceLinks} title="Validar estado de PostgreSQL"><NavIcon>DB</NavIcon><span>Database</span><span className="external-mark">↻</span></a><a className="nav-link" href="#services" onClick={validateServiceLinks} title="Validar estado de Redis"><NavIcon>RD</NavIcon><span>Redis</span><span className="external-mark">↻</span></a></nav>
        <div className="sidebar-bottom"><div className="sidebar-status-card"><div className="sidebar-status-heading"><StatusDot status={overallStatus} /><span>System status</span></div><strong>{error ? "Connection issue" : "All systems nominal"}</strong><span>{dashboard ? `Synced at ${formatTime(dashboard.fetchedAt)}` : "Waiting for API"}</span></div><button className="sidebar-user user-menu-button" type="button" onClick={onLogout}><span className="avatar">{userInitials}</span><span><strong>{displayName}</strong><small>Sign out securely</small></span><span className="more-mark">↗</span></button></div>
      </aside>

      <div className="main-viewport">
        <header className="page-header"><div className="breadcrumb"><span>Workspace</span><b>/</b><strong>Overview</strong></div><div className="header-actions"><span className="live-pill"><span /> Live environment</span><button className="theme-toggle" type="button" onClick={onThemeChange} aria-label={`Cambiar a modo ${theme === "dark" ? "claro" : "oscuro"}`} aria-pressed={theme === "light"} title={`Modo ${theme === "dark" ? "oscuro" : "claro"}`}><span className="theme-toggle-icon" aria-hidden="true">{theme === "dark" ? "☀" : "☾"}</span><span className="theme-toggle-label">{theme === "dark" ? "Claro" : "Oscuro"}</span></button><button className="refresh-button" type="button" onClick={() => loadDashboard(true)} disabled={refreshing}><span className={refreshing ? "spin-icon" : ""}>↻</span>{refreshing ? "Updating" : "Refresh"}</button><button className="header-user-button" type="button" onClick={onLogout} title="Cerrar sesión"><span className="header-avatar">{userInitials}</span><span className="header-user-name">{displayName}</span></button></div></header>
        <main className="dashboard-container" id="overview">
          <section className="welcome-row"><div><p className="section-kicker">{formatDate()}</p><h1>Good evening, <em>{displayName}.</em></h1><p className="welcome-copy">A clear view of your operational posture, signals and service health.</p></div><div className="last-sync"><span className="sync-line" /> Last sync <strong>{formatTime(dashboard?.fetchedAt)}</strong></div></section>
          <section className="executive-hero"><div className="hero-content"><div className="hero-tag"><span className="hero-tag-dot" /> FASE 3C / SECURE OPERATIONS</div><h2>Operational clarity<br /><span>at a glance.</span></h2><p>Monitor the pulse of your telemetry infrastructure and make better decisions with confidence.</p><div className="hero-actions"><a className="primary-action" href={`${API_BASE_URL}/api/v1/docs`} target="_blank" rel="noreferrer">Open API explorer <span>↗</span></a><a className="secondary-action" href="#services">View services</a></div></div><div className="hero-score-area"><div className="score-ring" style={{ "--score": `${healthScore}%` }}><div className="score-inner"><strong>{healthScore}</strong><span>health score</span></div></div><div className="hero-score-copy"><span className="score-status"><StatusDot status={overallStatus} />{statusLabel(overallStatus)}</span><small>Across {serviceConfig.length} core services</small></div></div><div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" /></section>
          <AlertPanel alerts={alerts} loading={alertsLoading} error={alertsError} connectionStatus={alertsConnectionStatus} lastEventAt={alertLastEventAt} acknowledgingId={acknowledgingId} onAcknowledge={acknowledge} />
          <IntegrationPanel session={session} />
          <MembersPanel session={session} />
          {error && <section className="error-banner" role="alert"><div><strong>Dashboard connection issue</strong><span>{error}. Check that the backend is available at {API_BASE_URL}.</span></div><button type="button" onClick={() => loadDashboard(true)}>Retry connection</button></section>}
          {loading && !dashboard ? <section className="loading-state" aria-live="polite"><span className="loader" /> Loading operational signals...</section> : <>
            <section className="kpi-grid" aria-label="Executive summary"><KpiCard label="Events processed" value={formatNumber(telemetryService.events_processed)} detail={`${formatNumber(telemetryService.batches_received)} batches received`} accent="blue" marker="01" /><KpiCard label="Success rate" value={formatPercent(telemetryService.success_rate)} detail={`${formatNumber(sentMessages)} messages sent`} accent="mint" marker="02" /><KpiCard label="Avg. processing" value={`${Number(telemetryService.avg_processing_time_ms || 0).toFixed(1)} ms`} detail="Telemetry pipeline latency" accent="violet" marker="03" /><KpiCard label="Queue depth" value={formatNumber(totalQueueDepth)} detail={`${formatNumber(processedMessages)} messages processed`} accent="amber" marker="04" /><KpiCard label="Open alerts" value={formatNumber(openAlertCount)} detail={`${formatNumber(highAlertCount)} high or critical`} accent="red" marker="05" /></section>
            <section className="section-heading" id="services"><div><p className="section-kicker">PLATFORM HEALTH</p><h2>Core services</h2></div><span className="section-meta"><span className="pulse-dot" /> Monitoring active</span></section>
            <section className="main-grid"><article className="panel service-panel"><div className="panel-heading"><div><span className="panel-index">01</span><div><p className="eyebrow">DEPENDENCIES</p><h3>Service health</h3></div></div><span className="panel-caption">{healthyServices}/{serviceConfig.length} online</span></div><div className="service-list">{serviceConfig.map(({ key, label, code, description }) => { const service = serviceStatuses[key] || {}; const status = key === "telemetry_service" ? service.status : service.healthy ? "healthy" : "unhealthy"; return <div className="service-row" key={key}><div className="service-leading"><span className="service-code">{code}</span><span><strong>{label}</strong><small>{description}</small></span></div><div className="service-trailing"><span className={`status-text status-text-${status}`}><StatusDot status={status} />{statusLabel(status)}</span><span className="service-arrow">→</span></div></div>; })}</div><div className="service-footer"><span>API endpoint</span><code>{API_BASE_URL}</code></div></article>
              <article className="panel signal-panel" id="telemetry"><div className="panel-heading"><div><span className="panel-index">02</span><div><p className="eyebrow">TELEMETRY SIGNAL</p><h3>Processing overview</h3></div></div><span className="panel-caption">Live data</span></div><div className="signal-summary"><div><span className="signal-number">{formatNumber(telemetryService.events_processed)}</span><span className="signal-label">events processed</span></div><div className="signal-delta"><span>Success</span><strong>{formatPercent(telemetryService.success_rate)}</strong></div></div><div className="signal-visual" aria-label="Telemetry processing signal visualization">{[36, 52, 44, 63, 58, 74, 67, 81, 72, 88, 79, 92].map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}<div className="signal-line" /></div><div className="signal-footer"><span><i className="legend-dot legend-blue" /> Current workload</span><span>Last 12 signal intervals</span></div></article></section>
            <section className="lower-grid"><article className="panel queue-panel"><div className="panel-heading"><div><span className="panel-index">03</span><div><p className="eyebrow">PROCESSING LAYER</p><h3>Queue activity</h3></div></div><span className="queue-badge">MOCK QUEUE</span></div><div className="queue-list">{queueNames.map((queueName) => { const depth = view.queueDepths[queueName] || 0; const fill = Math.min(depth * 10 + (depth === 0 ? 3 : 0), 100); return <div className="queue-row" key={queueName}><div className="queue-label"><span className="queue-icon" />{queueLabels[queueName] || queueName}</div><div className="queue-bar"><span style={{ width: `${fill}%` }} /></div><strong>{formatNumber(depth)}</strong></div>; })}</div></article><article className="panel activity-panel"><div className="panel-heading"><div><span className="panel-index">04</span><div><p className="eyebrow">SYSTEM LOG</p><h3>Current signals</h3></div></div><span className="live-indicator"><span /> LIVE</span></div><div className="activity-list">{alerts.length ? alerts.slice(0, 3).map((alert) => { const severity = alertSeverity(alert); const marker = ["critical", "high"].includes(severity) ? "marker-red" : severity === "medium" ? "marker-amber" : "marker-violet"; return <div className="activity-row" key={alert.id}><span className={`activity-marker ${marker}`} /><div><strong>{alert.title || "Operational alert"}</strong><small>{alert.description || "New intelligence signal detected"}</small></div><time>{alertStatus(alert).toUpperCase()}</time></div>; }) : <><div className="activity-row"><span className="activity-marker marker-mint" /><div><strong>All core services operational</strong><small>PostgreSQL, Redis and Telemetry engine are online</small></div><time>NOW</time></div><div className="activity-row"><span className="activity-marker marker-blue" /><div><strong>Telemetry pipeline ready</strong><small>Queue provider configured as local mock</small></div><time>READY</time></div><div className="activity-row"><span className="activity-marker marker-violet" /><div><strong>Secure session active</strong><small>{displayName} is authenticated with JWT</small></div><time>LIVE</time></div></>}</div></article></section>
          </>}
          <TeamPanel />
        </main>
        <footer className="app-footer">
          <div className="footer-primary"><span>SentinelMonitorIA <b>/</b> Executive operations console</span><span>© 2026 SentinelMonitorIA</span></div>
          <div className="footer-meta"><span>Última actualización: 23 de julio de 2026</span><span>Todos los derechos reservados <b>·</b> Fase 3C</span></div>
        </footer>
      </div>
      <ChatWidget session={session} />
    </div>
  );
}

function App() {
  const [session, setSession] = useState(() => readSession());
  const [authRestoring, setAuthRestoring] = useState(() => Boolean(readSession()));
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Continue without persistence when storage is unavailable.
    }
  }, [theme]);

  useEffect(() => {
    const storedSession = readSession();
    if (!storedSession) {
      setAuthRestoring(false);
      return undefined;
    }

    let active = true;
    restoreSession(storedSession).then((nextSession) => {
      if (active) setSession(nextSession);
    }).finally(() => {
      if (active) setAuthRestoring(false);
    });
    return () => { active = false; };
  }, []);

  const handleLogout = async () => {
    await logout(session);
    clearSession();
    setSession(null);
  };

  if (authRestoring) return <AuthLoading />;
  if (!session) return <AuthScreen onAuthenticated={setSession} />;
  return <Dashboard session={session} onLogout={handleLogout} theme={theme} onThemeChange={() => setTheme((current) => current === "dark" ? "light" : "dark")} />;
}

export { AuthScreen, IntegrationPanel, MembersPanel };
export default App;
