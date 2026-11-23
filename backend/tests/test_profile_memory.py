"""Tests SA-37 : profil du candidat retenu pendant la conversation et transmis au modèle."""
import httpx
import pytest

from app.services import llm_client
from app.services.chat_service import update_candidate_profile
from app.services.profile_extractor import (
    detect_language,
    extract_bac_section,
    extract_interests,
    extract_moyenne,
    extract_profile_updates,
    format_profile,
    merge_profile,
)


class FakeRedis:
    """Redis minimal en mémoire (get / set) pour tester le profil sans serveur Redis."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value


# --- Moyenne -------------------------------------------------------------

@pytest.mark.parametrize("message, attendu", [
    ("Ena moyenne 13 fel bac maths", 13.0),
    ("Je suis en terminale maths, moyenne générale 15,2.", 15.2),
    ("أنا في الباك علوم تجريبية، المعدّل متاعي 13.5", 13.5),
    ("j'ai eu 14/20 au bac", 14.0),
    ("Ah non pardon, moyenne mta3i 14.5 mchi 13", 14.5),
    ("Ma moyenne c'est pas 13 mais 14,5", 14.5),
    ("bonjour, je cherche une formation", None),
    ("w 9olli chnowa el moyenne mta3i", None),
    ("n7eb na3ref el moyenne mte3 el 3am li fet", None),
    ("moyenne 25", None),
])
def test_extract_moyenne(message, attendu):
    assert extract_moyenne(message) == attendu


# --- Section du bac, intérêts, langue -------------------------------------

@pytest.mark.parametrize("message, attendu", [
    ("Bonjour, je suis en terminale maths", "Mathématiques"),
    ("salut, ena bac info w n7eb nkammel fel ingénierie", "Sciences de l'informatique"),
    ("أنا في الباك علوم تجريبية", "Sciences expérimentales"),
    ("ena fel bac eco w gestion, moyenne 12", "Économie et gestion"),
    ("bac technique, moyenne 11", "Technique"),
    ("je cherche une formation en informatique", None),
])
def test_extract_bac_section(message, attendu):
    assert extract_bac_section(message) == attendu


def test_extract_interests_ignore_la_section_du_bac():
    assert extract_interests("ena fel bac eco w gestion, n7eb el informatique") == ["informatique"]
    assert extract_interests("J'ai bac info, nheb el cybersécurité w el réseaux") == ["cybersécurité", "réseaux"]
    assert extract_interests("J'aime surtout le développement web et l'IA.") == ["développement web", "intelligence artificielle"]


@pytest.mark.parametrize("message, attendu", [
    ("Bonjour, je voudrais des infos sur l'ISB", "français"),
    ("مرحبا، نحب نعرف على الهندسة", "tunisien (écriture arabe)"),
    ("ok mrigel, w ba3d nheb na3mel rdv", "Arabizi"),
    ("J'aime el informatique w el maths, mais nkhaf mel prépa", "mélange français et dialecte"),
    ("Can you answer in English please?", "anglais"),
])
def test_detect_language(message, attendu):
    assert detect_language(message) == attendu


# --- Fusion et résumé du profil ------------------------------------------

def test_merge_profile_ajoute_les_interets_et_remplace_le_reste():
    profil = {"moyenne": 13.0, "interets": ["informatique"]}
    profil = merge_profile(profil, {"moyenne": 14.5, "interets": ["informatique", "réseaux"]})
    assert profil == {"moyenne": 14.5, "interets": ["informatique", "réseaux"]}


def test_format_profile():
    texte = format_profile({"bac_section": "Mathématiques", "moyenne": 14.5, "interets": ["informatique"],
                            "status": "en_cours_d_orientation"})
    assert "Section du bac : Mathématiques" in texte
    assert "Moyenne : 14,5/20" in texte
    assert "Centres d'intérêt : informatique" in texte
    assert "status" not in texte
    assert format_profile({}) == ""
    assert format_profile({"status": "en_cours_d_orientation"}) == ""


# --- Mémoire dans la conversation (scénario MT-04 du jeu de test SA-32) ---

def test_le_profil_retient_la_correction_de_moyenne():
    redis = FakeRedis()
    update_candidate_profile(redis, "conv-1", "Ena moyenne 13 fel bac maths", first_message=True)
    profil = update_candidate_profile(redis, "conv-1", "Ah non pardon, moyenne mta3i 14.5 mchi 13")
    profil = update_candidate_profile(redis, "conv-1", "Chnowa les formations li tnasebni ? w 9olli chnowa el moyenne mta3i")

    assert profil["moyenne"] == 14.5
    assert profil["bac_section"] == "Mathématiques"
    assert profil["status"] == "en_cours_d_orientation"


def test_le_profil_s_enrichit_au_fil_des_messages():
    redis = FakeRedis()
    update_candidate_profile(redis, "conv-2", "Bonjour, je suis en terminale maths et je cherche une formation en informatique.")
    update_candidate_profile(redis, "conv-2", "J'aime surtout le développement web et l'IA.")
    profil = update_candidate_profile(redis, "conv-2", "Mais je préfère une voie plus pratique que théorique.")

    assert profil["bac_section"] == "Mathématiques"
    assert profil["interets"] == ["informatique", "développement web", "intelligence artificielle"]
    assert profil["preference"] == "formation pratique"


# --- Transmission du profil au modèle ------------------------------------

def test_generate_answer_envoie_le_profil_au_modele(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Bien noté."}},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    llm_client.generate_answer([{"role": "user", "content": "Chnowa les formations li tnasebni ?"}],
                               {"bac_section": "Mathématiques", "moyenne": 14.5})

    consignes = captured["json"]["messages"][0]["content"]
    assert consignes.startswith(llm_client.SYSTEM_PROMPT)
    assert "Moyenne : 14,5/20" in consignes
    assert "Section du bac : Mathématiques" in consignes


def test_generate_answer_sans_profil_garde_les_consignes_de_base(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Bonjour"}},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    llm_client.generate_answer([{"role": "user", "content": "Salut"}])
    assert captured["json"]["messages"][0]["content"] == llm_client.SYSTEM_PROMPT


def test_extract_profile_updates_message_complet():
    updates = extract_profile_updates("J'ai bac info, moyenne 16, nheb el cybersécurité w el réseaux, formation pratique avec stages")
    assert updates["bac_section"] == "Sciences de l'informatique"
    assert updates["moyenne"] == 16.0
    assert updates["interets"] == ["cybersécurité", "réseaux"]
    assert updates["preference"] == "formation pratique"
