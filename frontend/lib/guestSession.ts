import { ApiError, createGuestSession, getGuestSession } from "@/lib/api";

type GuestSessionCredentials = {
  guest_session_id: string;
  guest_token: string;
};

const SESSION_ID_KEY = "guest_session_id";
const SESSION_TOKEN_KEY = "guest_token";
const SESSION_INIT_LOCK = "smartcampus-guest-session-init";

let initializationPromise: Promise<GuestSessionCredentials> | null = null;

export function clearGuestSessionIfMatches(
  sessionId: string,
  guestToken: string,
) {
  if (typeof window === "undefined") return;

  if (localStorage.getItem(SESSION_ID_KEY) === sessionId) {
    localStorage.removeItem(SESSION_ID_KEY);
  }
  if (localStorage.getItem(SESSION_TOKEN_KEY) === guestToken) {
    localStorage.removeItem(SESSION_TOKEN_KEY);
  }
}

export function getOrCreateGuestSession(): Promise<GuestSessionCredentials> {
  if (initializationPromise) return initializationPromise;

  const request = withSessionInitializationLock(initializeGuestSession);
  const sharedRequest = request.finally(() => {
    if (initializationPromise === sharedRequest) {
      initializationPromise = null;
    }
  });
  initializationPromise = sharedRequest;
  return sharedRequest;
}

async function withSessionInitializationLock(
  initialize: () => Promise<GuestSessionCredentials>,
): Promise<GuestSessionCredentials> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    return await navigator.locks.request<Promise<GuestSessionCredentials>>(
      SESSION_INIT_LOCK,
      initialize,
    );
  }
  return initialize();
}

async function initializeGuestSession(): Promise<GuestSessionCredentials> {
  const savedSessionId = localStorage.getItem(SESSION_ID_KEY);
  const savedToken = localStorage.getItem(SESSION_TOKEN_KEY);

  if (!savedSessionId || !savedToken) {
    localStorage.removeItem(SESSION_ID_KEY);
    localStorage.removeItem(SESSION_TOKEN_KEY);
    return createAndStoreGuestSession();
  }

  try {
    await getGuestSession(savedSessionId, savedToken);
    return {
      guest_session_id: savedSessionId,
      guest_token: savedToken,
    };
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error;
    }
    clearGuestSessionIfMatches(savedSessionId, savedToken);
  }

  return createAndStoreGuestSession();
}

async function createAndStoreGuestSession(): Promise<GuestSessionCredentials> {
  const session = await createGuestSession();
  localStorage.setItem(SESSION_ID_KEY, session.guest_session_id);
  localStorage.setItem(SESSION_TOKEN_KEY, session.guest_token);
  return session;
}
