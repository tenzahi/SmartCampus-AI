const API_URL = process.env.NEXT_PUBLIC_API_URL;

// --- SESSIONS VISITEURS ---
export async function createGuestSession() {
  const res = await fetch(`${API_URL}/api/chat/sessions`, { method: 'POST' });
  if (!res.ok) throw new Error("Erreur de création de session");
  return res.json();
}

// --- CHAT ---
export async function sendMessage(sessionId: string, token: string, message: string) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x_guest_session': sessionId,
      'x_guest_token': token,
    },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Erreur d'envoi du message");
  return res.json();
}

// --- AUTHENTIFICATION ---
export async function login(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  if (!res.ok) throw new Error("Email ou mot de passe incorrect");
  return res.json(); // Contient { access_token, role }
}

// --- INSCRIPTION ---
export async function register(email: string, password: string, fullName: string) {
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  
  const data = await res.json();
  
  if (!res.ok) {
    // On récupère le message d'erreur du backend (ex: email déjà utilisé)
    throw new Error(data.detail || "Erreur lors de l'inscription");
  }
  return data;
}
// --- CLAIM (Rattachement) ---
export async function claimSession(sessionId: string, guestToken: string, jwtToken: string) {
  const res = await fetch(`${API_URL}/api/chat/sessions/${sessionId}/claim`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`,
    },
    body: JSON.stringify({ guest_token: guestToken, consent: true }),
  });
  if (!res.ok) throw new Error("Erreur lors du rattachement");
  return res.json();
}