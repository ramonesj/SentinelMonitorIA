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

export { API_BASE_URL };
