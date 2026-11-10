const API_URL = "http://127.0.0.1:8000";

export async function getHealth() {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error("Erreur lors de la connexion au backend");
  }

  return response.json();
}