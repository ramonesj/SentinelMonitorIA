import { useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE_URL, fetchDashboardData } from "./api";
import { clearSession, createApiKey, listApiKeys, login, logout, readSession, register, restoreSession, revokeApiKey, rotateApiKey } from "./auth";

const REFRESH_INTERVAL_MS = 30000;

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
  alerts: "Alerts",
  dead_letter: "Dead letter"
};

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
      await navigator.clipboard.writeText(generatedToken);
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
      {error && <div className="integration-error" role="alert">{error}</div>}
      <div className="integration-grid">
        <form className="integration-form" onSubmit={submit}>
          <label>Key name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Production agent" required /></label>
          <label>Expiration<select value={form.expiresInDays} onChange={(event) => setForm((current) => ({ ...current, expiresInDays: event.target.value }))}><option value="7">7 days</option><option value="30">30 days</option><option value="90">90 days</option><option value="365">365 days</option><option value="">No expiration</option></select></label>
          <div className="integration-org"><span>Organization</span><strong>{organization?.name || "Not configured"}</strong><small>{organization?.slug || "--"}</small></div>
          <button className="integration-submit" type="submit" disabled={submitting || !organization}>{submitting ? "Generating..." : "Generate API key"}<span>→</span></button>
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

function Dashboard({ session, onLogout }) {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const user = session.user || {};
  const userInitials = initialsFor(user);

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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="SentinelMonitorIA inicio"><span className="brand-mark"><span>S</span></span><span className="brand-copy"><strong>Sentinel<span>Monitor</span></strong><small>Intelligence platform</small></span></a>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="main-nav" aria-label="Navegación principal">
          <a className="nav-link active" href="#overview"><NavIcon>OV</NavIcon><span>Overview</span></a><a className="nav-link" href="#services"><NavIcon>SV</NavIcon><span>Services</span></a><a className="nav-link" href="#telemetry"><NavIcon>TP</NavIcon><span>Telemetry</span></a><a className="nav-link" href="#integrations"><NavIcon>AK</NavIcon><span>Connections</span></a><a className="nav-link" href={`${API_BASE_URL}/api/v1/docs`} target="_blank" rel="noreferrer"><NavIcon>API</NavIcon><span>API explorer</span><span className="external-mark">↗</span></a>
        </nav>
        <div className="sidebar-section-label sidebar-section-lower">Resources</div>
        <nav className="main-nav"><a className="nav-link" href="http://localhost:8080" target="_blank" rel="noreferrer"><NavIcon>DB</NavIcon><span>Database</span><span className="external-mark">↗</span></a><a className="nav-link" href="http://localhost:8081" target="_blank" rel="noreferrer"><NavIcon>RD</NavIcon><span>Redis</span><span className="external-mark">↗</span></a></nav>
        <div className="sidebar-bottom"><div className="sidebar-status-card"><div className="sidebar-status-heading"><StatusDot status={overallStatus} /><span>System status</span></div><strong>{error ? "Connection issue" : "All systems nominal"}</strong><span>{dashboard ? `Synced at ${formatTime(dashboard.fetchedAt)}` : "Waiting for API"}</span></div><button className="sidebar-user user-menu-button" type="button" onClick={onLogout}><span className="avatar">{userInitials}</span><span><strong>{displayName}</strong><small>Sign out securely</small></span><span className="more-mark">↗</span></button></div>
      </aside>

      <div className="main-viewport">
        <header className="page-header"><div className="breadcrumb"><span>Workspace</span><b>/</b><strong>Overview</strong></div><div className="header-actions"><span className="live-pill"><span /> Live environment</span><button className="refresh-button" type="button" onClick={() => loadDashboard(true)} disabled={refreshing}><span className={refreshing ? "spin-icon" : ""}>↻</span>{refreshing ? "Updating" : "Refresh"}</button><button className="header-user-button" type="button" onClick={onLogout} title="Cerrar sesión"><span className="header-avatar">{userInitials}</span><span className="header-user-name">{displayName}</span></button></div></header>
        <main className="dashboard-container" id="overview">
          <section className="welcome-row"><div><p className="section-kicker">{formatDate()}</p><h1>Good evening, <em>{displayName}.</em></h1><p className="welcome-copy">A clear view of your operational posture, signals and service health.</p></div><div className="last-sync"><span className="sync-line" /> Last sync <strong>{formatTime(dashboard?.fetchedAt)}</strong></div></section>
          <section className="executive-hero"><div className="hero-content"><div className="hero-tag"><span className="hero-tag-dot" /> FASE 3C / SECURE OPERATIONS</div><h2>Operational clarity<br /><span>at a glance.</span></h2><p>Monitor the pulse of your telemetry infrastructure and make better decisions with confidence.</p><div className="hero-actions"><a className="primary-action" href={`${API_BASE_URL}/api/v1/docs`} target="_blank" rel="noreferrer">Open API explorer <span>↗</span></a><a className="secondary-action" href="#services">View services</a></div></div><div className="hero-score-area"><div className="score-ring" style={{ "--score": `${healthScore}%` }}><div className="score-inner"><strong>{healthScore}</strong><span>health score</span></div></div><div className="hero-score-copy"><span className="score-status"><StatusDot status={overallStatus} />{statusLabel(overallStatus)}</span><small>Across {serviceConfig.length} core services</small></div></div><div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" /></section>
          <IntegrationPanel session={session} />
          {error && <section className="error-banner" role="alert"><div><strong>Dashboard connection issue</strong><span>{error}. Check that the backend is available at {API_BASE_URL}.</span></div><button type="button" onClick={() => loadDashboard(true)}>Retry connection</button></section>}
          {loading && !dashboard ? <section className="loading-state" aria-live="polite"><span className="loader" /> Loading operational signals...</section> : <>
            <section className="kpi-grid" aria-label="Executive summary"><KpiCard label="Events processed" value={formatNumber(telemetryService.events_processed)} detail={`${formatNumber(telemetryService.batches_received)} batches received`} accent="blue" marker="01" /><KpiCard label="Success rate" value={formatPercent(telemetryService.success_rate)} detail={`${formatNumber(sentMessages)} messages sent`} accent="mint" marker="02" /><KpiCard label="Avg. processing" value={`${Number(telemetryService.avg_processing_time_ms || 0).toFixed(1)} ms`} detail="Telemetry pipeline latency" accent="violet" marker="03" /><KpiCard label="Queue depth" value={formatNumber(totalQueueDepth)} detail={`${formatNumber(processedMessages)} messages processed`} accent="amber" marker="04" /></section>
            <section className="section-heading" id="services"><div><p className="section-kicker">PLATFORM HEALTH</p><h2>Core services</h2></div><span className="section-meta"><span className="pulse-dot" /> Monitoring active</span></section>
            <section className="main-grid"><article className="panel service-panel"><div className="panel-heading"><div><span className="panel-index">01</span><div><p className="eyebrow">DEPENDENCIES</p><h3>Service health</h3></div></div><span className="panel-caption">{healthyServices}/{serviceConfig.length} online</span></div><div className="service-list">{serviceConfig.map(({ key, label, code, description }) => { const service = serviceStatuses[key] || {}; const status = key === "telemetry_service" ? service.status : service.healthy ? "healthy" : "unhealthy"; return <div className="service-row" key={key}><div className="service-leading"><span className="service-code">{code}</span><span><strong>{label}</strong><small>{description}</small></span></div><div className="service-trailing"><span className={`status-text status-text-${status}`}><StatusDot status={status} />{statusLabel(status)}</span><span className="service-arrow">→</span></div></div>; })}</div><div className="service-footer"><span>API endpoint</span><code>{API_BASE_URL}</code></div></article>
              <article className="panel signal-panel" id="telemetry"><div className="panel-heading"><div><span className="panel-index">02</span><div><p className="eyebrow">TELEMETRY SIGNAL</p><h3>Processing overview</h3></div></div><span className="panel-caption">Live data</span></div><div className="signal-summary"><div><span className="signal-number">{formatNumber(telemetryService.events_processed)}</span><span className="signal-label">events processed</span></div><div className="signal-delta"><span>Success</span><strong>{formatPercent(telemetryService.success_rate)}</strong></div></div><div className="signal-visual" aria-label="Telemetry processing signal visualization">{[36, 52, 44, 63, 58, 74, 67, 81, 72, 88, 79, 92].map((height, index) => <span key={index} style={{ height: `${height}%` }} />)}<div className="signal-line" /></div><div className="signal-footer"><span><i className="legend-dot legend-blue" /> Current workload</span><span>Last 12 signal intervals</span></div></article></section>
            <section className="lower-grid"><article className="panel queue-panel"><div className="panel-heading"><div><span className="panel-index">03</span><div><p className="eyebrow">PROCESSING LAYER</p><h3>Queue activity</h3></div></div><span className="queue-badge">MOCK QUEUE</span></div><div className="queue-list">{queueNames.map((queueName) => { const depth = view.queueDepths[queueName] || 0; const fill = Math.min(depth * 10 + (depth === 0 ? 3 : 0), 100); return <div className="queue-row" key={queueName}><div className="queue-label"><span className="queue-icon" />{queueLabels[queueName] || queueName}</div><div className="queue-bar"><span style={{ width: `${fill}%` }} /></div><strong>{formatNumber(depth)}</strong></div>; })}</div></article><article className="panel activity-panel"><div className="panel-heading"><div><span className="panel-index">04</span><div><p className="eyebrow">SYSTEM LOG</p><h3>Current signals</h3></div></div><span className="live-indicator"><span /> LIVE</span></div><div className="activity-list"><div className="activity-row"><span className="activity-marker marker-mint" /><div><strong>All core services operational</strong><small>PostgreSQL, Redis and Telemetry engine are online</small></div><time>NOW</time></div><div className="activity-row"><span className="activity-marker marker-blue" /><div><strong>Telemetry pipeline ready</strong><small>Queue provider configured as local mock</small></div><time>READY</time></div><div className="activity-row"><span className="activity-marker marker-violet" /><div><strong>Secure session active</strong><small>{displayName} is authenticated with JWT</small></div><time>LIVE</time></div></div></article></section>
          </>}
        </main>
        <footer className="app-footer"><span>SentinelMonitorIA <b>/</b> Executive operations console</span><span>Secure workspace <b>·</b> Fase 3C</span></footer>
      </div>
    </div>
  );
}

function App() {
  const [session, setSession] = useState(() => readSession());
  const [authRestoring, setAuthRestoring] = useState(() => Boolean(readSession()));

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
  return <Dashboard session={session} onLogout={handleLogout} />;
}

export default App;
