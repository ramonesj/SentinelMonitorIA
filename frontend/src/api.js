const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getJson(path, accessToken) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${path} respondió HTTP ${response.status}`);
  }

  return response.json();
}

async function getMetrics(accessToken) {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    headers: {
      Accept: "text/plain",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`/metrics respondió HTTP ${response.status}`);
  }

  return response.text();
}

export function parsePrometheusMetrics(metricsText) {
  const metrics = {};
  const linePattern = /^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^}]*\})?\s+([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$/;

  metricsText.split("\n").forEach((line) => {
    const match = line.trim().match(linePattern);
    if (match) {
      const [, name, value] = match;
      if (metrics[name] === undefined) metrics[name] = Number(value);
    }
  });

  return metrics;
}

export async function fetchDashboardData(accessToken) {
  const [health, telemetryHealth, telemetryStats, metricsText] = await Promise.all([
    getJson("/health", accessToken),
    getJson("/api/v1/telemetry/health", accessToken),
    getJson("/api/v1/telemetry/stats", accessToken),
    getMetrics(accessToken)
  ]);

  return {
    health,
    telemetryHealth,
    telemetryStats,
    metrics: parsePrometheusMetrics(metricsText),
    fetchedAt: new Date()
  };
}

export async function fetchAlerts(accessToken, limit = 50) {
  const normalizedLimit = Math.min(Math.max(Number(limit) || 50, 1), 100);
  const response = await getJson(`/api/v1/alerts?limit=${normalizedLimit}`, accessToken);
  return response.alerts || [];
}

export async function acknowledgeAlert(accessToken, alertId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `/api/v1/alerts/${alertId}/acknowledge respondió HTTP ${response.status}`);
  }

  return response.json();
}

export async function sendChatMessage(accessToken, payload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `/api/v1/chat respondió HTTP ${response.status}`);
  }

  return response.json();
}

export function getAlertsWebSocketUrl() {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/api/v1/alerts/ws`;
  url.search = "";
  return url.toString();
}

export function connectAlertsWebSocket(accessToken) {
  if (typeof WebSocket === "undefined" || !accessToken) return null;

  const socket = new WebSocket(getAlertsWebSocketUrl());
  socket.addEventListener("open", () => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "authenticate", access_token: accessToken }));
    }
  }, { once: true });
  return socket;
}

export { API_BASE_URL };
