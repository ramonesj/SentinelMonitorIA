import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  acceptOrganizationInvitation,
  createOrganizationInvitation,
  login,
  readSession,
  restoreSession
} from "./auth";

function response(body, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    json: async () => body
  };
}

describe("frontend authentication and invitation contracts", () => {
  beforeEach(() => {
    window.localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  it("persists a successful login session and sends the expected credentials", async () => {
    const session = {
      access_token: "access-token",
      refresh_token: "refresh-token",
      user: { username: "operator" }
    };
    globalThis.fetch.mockResolvedValue(response(session));

    await expect(login({ username: "operator", password: "Secret!2026" })).resolves.toEqual(session);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "operator", password: "Secret!2026" })
      })
    );
    expect(readSession()).toEqual(session);
  });

  it("refreshes a session after an expired access token", async () => {
    const session = {
      access_token: "expired-access",
      refresh_token: "refresh-token",
      user: { username: "operator" }
    };
    const refreshedTokens = { access_token: "new-access", refresh_token: "new-refresh" };
    const currentUser = { username: "operator", organizations: [] };
    globalThis.fetch
      .mockResolvedValueOnce(response({ detail: "expired" }, { ok: false, status: 401 }))
      .mockResolvedValueOnce(response(refreshedTokens))
      .mockResolvedValueOnce(response(currentUser));

    await expect(restoreSession(session)).resolves.toEqual({
      ...session,
      ...refreshedTokens,
      user: currentUser
    });

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/v1/auth/refresh",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refresh_token: "refresh-token" })
      })
    );
    expect(readSession()).toEqual({ ...session, ...refreshedTokens, user: currentUser });
  });

  it("formats API validation errors with their HTTP status", async () => {
    globalThis.fetch.mockResolvedValue(
      response(
        { detail: [{ msg: "Email inválido" }, { msg: "Campo requerido" }] },
        { ok: false, status: 422 }
      )
    );

    await expect(login({ username: "operator", password: "bad" })).rejects.toMatchObject({
      message: "Email inválido. Campo requerido",
      status: 422
    });
  });

  it("uses organization-scoped invitation endpoints with the bearer token", async () => {
    const session = { access_token: "access-token" };
    const invitationData = { email: "invitee@example.com", role: "viewer", expires_in_days: 7 };
    globalThis.fetch
      .mockResolvedValueOnce(response({ id: "inv-1", token: "one-time-token" }))
      .mockResolvedValueOnce(response({ organization_id: "org-1", role: "viewer" }));

    await createOrganizationInvitation(session, "org-1", invitationData);
    await acceptOrganizationInvitation(session, "one-time-token");

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/v1/organizations/org-1/invitations",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(invitationData),
        headers: expect.objectContaining({ Authorization: "Bearer access-token" })
      })
    );
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/v1/auth/invitations/accept",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ token: "one-time-token" }),
        headers: expect.objectContaining({ Authorization: "Bearer access-token" })
      })
    );
  });
});
