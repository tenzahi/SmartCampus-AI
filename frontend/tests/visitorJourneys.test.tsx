import type { ReactNode } from "react";
import { StrictMode } from "react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const apiMocks = vi.hoisted(() => ({
  createGuestSession: vi.fn(),
  getGuestSession: vi.fn(),
  getMyConversations: vi.fn(),
  getMyConversation: vi.fn(),
  claimSession: vi.fn(),
  sendMessage: vi.fn(),
}));
const authMocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  ...apiMocks,
}));
vi.mock("@/lib/AuthContext", () => authMocks);
vi.mock("@/components/Navbar", () => ({ default: () => null }));
vi.mock("@/components/CandidatePage", () => ({
  default: ({
    title,
    description,
    children,
  }: {
    title: string;
    description?: string;
    children?: ReactNode;
  }) => (
    <main>
      <h1>{title}</h1>
      {description && <p>{description}</p>}
      {children}
    </main>
  ),
}));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: ReactNode;
  }) => <a href={href}>{children}</a>,
}));

import Home from "@/app/page";
import CandidateChatPage from "@/app/candidate/chat/page";
import CandidateDashboardPage from "@/app/candidate/dashboard/page";
import { ApiError } from "@/lib/api";

const candidateAuth = {
  token: "candidate-jwt",
  user: { id: 7, email: "candidate@example.com", role: "candidate" },
  role: "candidate",
  isLoading: false,
  authError: null,
  loginUser: vi.fn(),
  logout: vi.fn(),
  clearAuthError: vi.fn(),
};

describe("EPIC 23 visitor journeys", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMocks.useAuth.mockReturnValue(candidateAuth);
    apiMocks.getMyConversations.mockResolvedValue([]);
    apiMocks.getGuestSession.mockResolvedValue({
      guest_session_id: "guest-1",
      status: "active",
      expires_at: "2026-11-28T00:00:00+00:00",
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("creates and stores a visitor session", async () => {
    apiMocks.createGuestSession.mockResolvedValue({
      guest_session_id: "guest-1",
      guest_token: "opaque-guest-token",
    });

    render(
      <StrictMode>
        <Home />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(localStorage.getItem("guest_session_id")).toBe("guest-1");
    });
    expect(localStorage.getItem("guest_token")).toBe("opaque-guest-token");
    expect(apiMocks.createGuestSession).toHaveBeenCalledOnce();
  });

  it("reuses a valid saved visitor session", async () => {
    localStorage.setItem("guest_session_id", "guest-1");
    localStorage.setItem("guest_token", "opaque-guest-token");

    render(
      <StrictMode>
        <Home />
      </StrictMode>,
    );

    await screen.findByText(/Bonjour ! Je suis SmartCampus AI/i);
    expect(apiMocks.getGuestSession).toHaveBeenCalledOnce();
    expect(apiMocks.createGuestSession).not.toHaveBeenCalled();
  });

  it("replaces a saved session only after a definitive 401", async () => {
    localStorage.setItem("guest_session_id", "guest-expired");
    localStorage.setItem("guest_token", "expired-token");
    apiMocks.getGuestSession.mockRejectedValue(
      new ApiError("Session invalide ou expirée", 401),
    );
    apiMocks.createGuestSession.mockResolvedValue({
      guest_session_id: "guest-2",
      guest_token: "new-token",
    });

    render(
      <StrictMode>
        <Home />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(localStorage.getItem("guest_session_id")).toBe("guest-2");
    });
    expect(localStorage.getItem("guest_token")).toBe("new-token");
    expect(apiMocks.getGuestSession).toHaveBeenCalledOnce();
    expect(apiMocks.createGuestSession).toHaveBeenCalledOnce();
  });

  it.each([
    ["network failure", 0],
    ["server failure", 500],
  ])("does not create a session after a %s", async (_label, status) => {
    localStorage.setItem("guest_session_id", "guest-existing");
    localStorage.setItem("guest_token", "existing-token");
    apiMocks.getGuestSession.mockRejectedValue(
      new ApiError("Échec de vérification", status),
    );

    render(
      <StrictMode>
        <Home />
      </StrictMode>,
    );

    expect(await screen.findByText("Échec de vérification")).toBeInTheDocument();
    expect(apiMocks.getGuestSession).toHaveBeenCalledOnce();
    expect(apiMocks.createGuestSession).not.toHaveBeenCalled();
    expect(localStorage.getItem("guest_session_id")).toBe("guest-existing");
    expect(localStorage.getItem("guest_token")).toBe("existing-token");
  });

  it("claims a visitor conversation only after explicit consent", async () => {
    localStorage.setItem("guest_session_id", "guest-1");
    localStorage.setItem("guest_token", "opaque-guest-token");
    apiMocks.claimSession.mockResolvedValue({
      status: "claimed",
      guest_session_id: "guest-1",
      conversation_ids: ["conversation-1"],
    });

    render(<CandidateDashboardPage />);
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", {
        name: "Je consens et je rattache",
      }),
    );

    expect(apiMocks.claimSession).toHaveBeenCalledWith(
      "guest-1",
      "opaque-guest-token",
      "candidate-jwt",
    );
    expect(
      await screen.findByText(/session visiteur rattachée/i),
    ).toBeInTheDocument();
    expect(
      JSON.parse(
        localStorage.getItem("candidate_claimed_session_7") || "null",
      ),
    ).toMatchObject({
      sessionId: "guest-1",
      guestToken: "opaque-guest-token",
      candidateId: 7,
    });
    expect(localStorage.getItem("guest_session_id")).toBeNull();
    expect(localStorage.getItem("guest_token")).toBeNull();
  });

  it("does not claim a visitor conversation when consent is declined", async () => {
    localStorage.setItem("guest_session_id", "guest-1");
    localStorage.setItem("guest_token", "opaque-guest-token");
    render(<CandidateDashboardPage />);
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Ne pas rattacher" }),
    );

    expect(apiMocks.claimSession).not.toHaveBeenCalled();
    expect(localStorage.getItem("guest_session_id")).toBeNull();
    expect(localStorage.getItem("guest_token")).toBeNull();
  });

  it("shows a clear error when an expired claimed session rejects chat", async () => {
    localStorage.setItem(
      "candidate_claimed_session_7",
      JSON.stringify({
        sessionId: "guest-1",
        guestToken: "opaque-guest-token",
        candidateId: 7,
      }),
    );
    apiMocks.sendMessage.mockRejectedValue(
      new ApiError("Session invalide ou expirée", 401),
    );
    render(<CandidateChatPage />);
    const user = userEvent.setup();

    await user.type(
      await screen.findByRole("textbox", { name: "Votre message" }),
      "Ma question",
    );
    await user.click(screen.getByRole("button", { name: "Envoyer le message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Session invalide ou expirée",
    );
    expect(apiMocks.sendMessage).toHaveBeenCalledWith(
      "guest-1",
      "opaque-guest-token",
      "Ma question",
      "candidate-jwt",
    );
  });
});
