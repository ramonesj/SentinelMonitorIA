import { API_BASE_URL } from "./api";

const SESSION_KEY = "sentinelmonitoria.session";

function errorFromResponse(response, body) {
  const detail = body?.detail;
  const message = Array.isArray(detail)
    ? detail.map((item) => item.msg).join(". ")
    : detail || body?.message || `Solicitud rechazada (HTTP ${response.status})`;
  const error = new Error(message);
  error.status = response.status;
  return error;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const body = await response.json().catch(() => ({}));

  if (!response.ok) throw errorFromResponse(response, body);
  return body;
}

function persistSession(session) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export function readSession() {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    window.localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function clearSession() {
  window.localStorage.removeItem(SESSION_KEY);
}

export async function login(credentials) {
  const session = await request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials)
  });
  return persistSession(session);
}

export async function register(registration) {
  const session = await request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(registration)
  });
  return persistSession(session);
}

export async function refreshSession(session) {
  const tokens = await request("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: session.refresh_token })
  });
  return persistSession({ ...session, ...tokens });
}

export async function getCurrentUser(accessToken) {
  return request("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
}

export async function restoreSession(session) {
  if (!session?.access_token) return null;

  try {
    const user = await getCurrentUser(session.access_token);
    return persistSession({ ...session, user });
  } catch (error) {
    if (error.status !== 401 || !session.refresh_token) {
      clearSession();
      return null;
    }

    try {
      const refreshed = await refreshSession(session);
      const user = await getCurrentUser(refreshed.access_token);
      return persistSession({ ...refreshed, user });
    } catch {
      clearSession();
      return null;
    }
  }
}

export async function logout(session) {
  try {
    if (session?.access_token) {
      await request("/api/v1/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` }
      });
    }
  } finally {
    clearSession();
  }
}


export async function createApiKey(session, tokenData) {
  return request("/api/v1/auth/api-keys", {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: JSON.stringify(tokenData)
  });
}

export async function listApiKeys(session) {
  return request("/api/v1/auth/api-keys", {
    headers: { Authorization: `Bearer ${session.access_token}` }
  });
}

export async function revokeApiKey(session, tokenId) {
  return request(`/api/v1/auth/api-keys/${tokenId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${session.access_token}` }
  });
}


export async function rotateApiKey(session, tokenId, options = {}) {
  return request(`/api/v1/auth/api-keys/${tokenId}/rotate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: JSON.stringify(options)
  });
}
