import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./auth", () => ({
  clearSession: vi.fn(),
  createApiKey: vi.fn(),
  listApiKeys: vi.fn(),
  listOrganizationMembers: vi.fn(),
  addOrganizationMember: vi.fn(),
  updateOrganizationMember: vi.fn(),
  removeOrganizationMember: vi.fn(),
  createOrganizationInvitation: vi.fn(),
  listOrganizationInvitations: vi.fn(),
  revokeOrganizationInvitation: vi.fn(),
  acceptOrganizationInvitation: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  readSession: vi.fn(() => null),
  register: vi.fn(),
  restoreSession: vi.fn(),
  revokeApiKey: vi.fn(),
  rotateApiKey: vi.fn()
}));

vi.mock("./api", () => ({
  API_BASE_URL: "http://localhost:8000",
  fetchDashboardData: vi.fn()
}));

import { IntegrationPanel, MembersPanel } from "./App";
import * as auth from "./auth";

const adminSession = {
  access_token: "admin-access",
  user: {
    id: "user-admin",
    username: "admin",
    organizations: [{ id: "org-1", name: "Sentinel", slug: "sentinel", role: "admin" }]
  }
};

const viewerSession = {
  access_token: "viewer-access",
  user: {
    id: "user-viewer",
    username: "viewer",
    organizations: [{ id: "org-1", name: "Sentinel", slug: "sentinel", role: "viewer" }]
  }
};

const member = {
  id: "member-1",
  username: "member",
  email: "member@example.com",
  full_name: "Team Member",
  role: "member"
};

describe("organization access UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.listOrganizationMembers.mockResolvedValue([member]);
    auth.listOrganizationInvitations.mockResolvedValue([]);
    auth.listApiKeys.mockResolvedValue({ tokens: [] });
  });

  it("shows member and invitation management controls to an admin", async () => {
    render(<MembersPanel session={adminSession} />);

    expect(await screen.findByText("1 members")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create invitation/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /add member/i })).toBeEnabled();
  });

  it("hides member and invitation management controls from a viewer", async () => {
    render(<MembersPanel session={viewerSession} />);

    expect(await screen.findByText("1 members")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create invitation/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add member/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /accept invitation/i })).toBeInTheDocument();
  });

  it("disables API key generation for a viewer", async () => {
    render(<IntegrationPanel session={viewerSession} />);

    expect(await screen.findByText("0 configured")).toBeInTheDocument();
    expect(screen.getByText(/sólo los administradores y managers/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate api key/i })).toBeDisabled();
  });

  it("creates an invitation and displays its one-time token for an admin", async () => {
    const invitation = {
      id: "inv-1",
      email: "invitee@example.com",
      role: "member",
      status: "pending",
      expires_at: "2026-08-01T00:00:00Z"
    };
    auth.createOrganizationInvitation.mockResolvedValue({ id: "inv-1", token: "one-time-token" });
    auth.listOrganizationInvitations
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([invitation]);

    render(<MembersPanel session={adminSession} />);
    await screen.findByText("No hay invitaciones todavía.");

    fireEvent.change(screen.getByLabelText("Email del invitado"), {
      target: { value: "invitee@example.com" }
    });
    fireEvent.click(screen.getByRole("button", { name: /create invitation/i }));

    await waitFor(() => {
      expect(auth.createOrganizationInvitation).toHaveBeenCalledWith(
        adminSession,
        "org-1",
        { email: "invitee@example.com", role: "member", expires_in_days: 7 }
      );
    });
    expect(await screen.findByText("one-time-token")).toBeInTheDocument();
  });
});
