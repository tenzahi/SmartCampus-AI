# -*- coding: utf-8 -*-
"""SA-38 : tester le dialogue multi-tours du chat SmartCampus AI avec le LLM.

Le script rejoue les 5 conversations du jeu de test SA-32 (feuille « Dialogues »)
sur le vrai chat (API du backend, donc gemma4:e4b + mémoire Redis + profil SA-37),
puis vérifie automatiquement les points clés de chaque scénario.

Prérequis : le projet tourne (docker compose up -d) et le modèle est chargé
(docker compose exec ollama ollama ps affiche gemma4:e4b). Le script crée une
session visiteur par scénario : la limite anti-abus est de 5 sessions par jour
et par adresse IP (variable GUEST_SESSION_MAX_PER_IP).

Usage (depuis la racine du projet) :
    python evaluation/llm/test_dialogues.py
    python evaluation/llm/test_dialogues.py --scenarios MT-04
Résultat : evaluation/llm/resultats/SA-38_resultats_dialogues.xlsx et .json
"""
import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = ROOT / "docs" / "SA-31_Selection_LLM" / "SA-32-donnees de test" / "SA-32 — Jeu de test LLM.xlsx"
OUT_DIR = Path(__file__).resolve().parent / "resultats"
API = "http://localhost:8000"
FALLBACK = "Désolé, je ne peux pas répondre"

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-zÀ-ÿ]")
ENGLISH = re.compile(r"\b(the|you|your|and|is|are|to|for|with|can|i|in|about|please|would|what)\b", re.I)
INVENTED_THRESHOLD = re.compile(r"\b\d{1,2}(?:[.,]\d+)?\s*/\s*20\b")
RDV = re.compile(r"rendez[- ]vous|\brdv\b|موعد|مواعيد|maw3ed|appointment|meeting", re.I)
INSCRIPTION = re.compile(r"pr[ée]inscription|inscription|تسجيل|ta?sjil", re.I)


def arabic_ratio(text):
    a, l = len(ARABIC.findall(text)), len(LATIN.findall(text))
    return a / (a + l) if a + l else 0


def english_ratio(text):
    words = re.findall(r"[A-Za-zÀ-ÿ']+", text)
    return len(ENGLISH.findall(text)) / len(words) if words else 0


def thresholds(text, allowed=()):
    """Notes sur 20 citées par le modèle, hors notes données par le candidat."""
    found = {m.group(0).replace(" ", "").replace(",", ".") for m in INVENTED_THRESHOLD.finditer(text)}
    return sorted(v for v in found if v.split("/")[0] not in allowed)


# Contrôles automatiques : (scénario, tour, libellé, fonction(réponse, profil) -> bool)
CHECKS = [
    ("MT-01", 4, "Rappelle les préférences : web, IA et pratique",
     lambda a, p: bool(re.search(r"\bweb\b", a, re.I) and re.search(r"\bIA\b|intelligence artificielle", a, re.I)
                       and re.search(r"pratique", a, re.I))),
    ("MT-01", 4, "Profil retenu : bac maths, web, IA, pratique",
     lambda a, p: p.get("bac_section") == "Mathématiques" and {"développement web", "intelligence artificielle"} <= set(p.get("interets", []))
     and p.get("preference") == "formation pratique"),
    ("MT-02", 2, "Comprend « conditions » pour l'ingénierie sans seuil inventé",
     lambda a, p: bool(re.search(r"ing[ée]ni|هندسة", a, re.I)) and not thresholds(a)),
    ("MT-02", 4, "Traite la demande de préinscription",
     lambda a, p: bool(INSCRIPTION.search(a))),
    ("MT-02", 4, "Profil retenu : bac informatique",
     lambda a, p: p.get("bac_section") == "Sciences de l'informatique"),
    ("MT-03", 1, "Répond en écriture arabe", lambda a, p: arabic_ratio(a) > 0.5),
    ("MT-03", 2, "Répond en écriture arabe à « قداش تدوم »", lambda a, p: arabic_ratio(a) > 0.5),
    ("MT-03", 3, "Répond en écriture arabe", lambda a, p: arabic_ratio(a) > 0.5),
    ("MT-03", 4, "Traite la demande de rendez-vous", lambda a, p: bool(RDV.search(a))),
    ("MT-04", 2, "Prend en compte la correction (14,5)", lambda a, p: bool(re.search(r"14[.,]5", a))),
    ("MT-04", 3, "Utilise 14,5 et non 13", lambda a, p: bool(re.search(r"14[.,]5", a)) and not re.search(r"\b13\s*/\s*20", a)),
    ("MT-04", 3, "Profil retenu : moyenne 14,5", lambda a, p: p.get("moyenne") == 14.5),
    ("MT-05", 2, "Passe à l'anglais quand on le demande", lambda a, p: english_ratio(a) > 0.15),
    ("MT-05", 3, "Revient au français ou au dialecte", lambda a, p: english_ratio(a) < 0.15),
    ("MT-05", 3, "Traite la demande de rendez-vous", lambda a, p: bool(RDV.search(a))),
]


def post(path, payload=None, headers=None, timeout=600):
    data = json.dumps(payload).encode("utf-8") if payload is not None else b""
    req = urllib.request.Request(API + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def read_profile(conv_id):
    """Lit le profil enregistré dans Redis (conteneur smartcampus-redis)."""
    try:
        out = subprocess.run(["docker", "compose", "exec", "-T", "redis", "redis-cli", "--raw", "GET", f"conv:{conv_id}:profile"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30).stdout.strip()
        return json.loads(out) if out else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def load_dialogues(path):
    dialogues = {}
    for row in load_workbook(path, data_only=True)["Dialogues"].iter_rows(min_row=5, values_only=True):
        if row[0]:
            dialogues.setdefault(row[0], {"theme": row[1], "turns": []})["turns"].append(
                {"tour": int(row[2]), "message": row[3], "attendu": row[4]})
    return dialogues


def run(scenarios):
    dialogues = load_dialogues(TEST_FILE)
    results = []
    for sid, d in dialogues.items():
        if scenarios and sid not in scenarios:
            continue
        try:
            session = post("/api/chat/sessions")   # une session visiteur neuve par scénario
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise SystemExit(
                    "Limite de 5 sessions visiteur par jour et par IP atteinte (guest_session_max_per_ip).\n"
                    "Pour le test, relancer le backend avec GUEST_SESSION_MAX_PER_IP plus élevé, ou réessayer demain.") from exc
            raise
        headers = {"x-guest-session": session["guest_session_id"], "x-guest-token": session["guest_token"]}
        print(f"\n=== {sid} — {d['theme']}")
        for t in d["turns"]:
            t0 = time.time()
            reply = post("/api/chat", {"message": t["message"]}, headers)
            latency = round(time.time() - t0, 1)
            if reply["answer"].startswith("J'ai bien noté votre message"):
                raise SystemExit("Le backend renvoie encore les réponses simulées d'avant SA-36 : "
                                 "vérifier la branche (git status) et redémarrer le backend.")
            profile = read_profile(reply["conversation_id"])
            results.append({"scenario": sid, "theme": d["theme"], "tour": t["tour"], "message": t["message"],
                            "attendu": t["attendu"], "reponse": reply["answer"], "latence_s": latency,
                            "taille_contexte": reply.get("context_size"), "profil": profile,
                            "secours": reply["answer"].startswith(FALLBACK),
                            "seuils_cites": thresholds(reply["answer"], allowed={"13", "14.5", "14"})})
            print(f"  T{t['tour']} ({latency} s) {reply['answer'][:90]!r}")
    return results


def evaluate(results):
    by_turn = {(r["scenario"], r["tour"]): r for r in results}
    checks = []
    for sid, tour, label, fn in CHECKS:
        r = by_turn.get((sid, tour))
        if r:
            checks.append({"scenario": sid, "tour": tour, "controle": label, "reussi": bool(fn(r["reponse"], r["profil"]))})
    return checks


def save(results, checks):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "SA-38_resultats_dialogues.json").write_text(
        json.dumps({"reponses": results, "controles": checks}, ensure_ascii=False, indent=1), encoding="utf-8")

    thin = Side(style="thin", color="A6A6A6")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="E6E6E6")
    wb = Workbook()

    def sheet(ws, headers, widths, rows):
        for j, (h, w) in enumerate(zip(headers, widths), 1):
            c = ws.cell(1, j, h)
            c.font, c.fill, c.border = Font(name="Calibri", bold=True), head_fill, border
            c.alignment = Alignment(wrap_text=True, vertical="center")
            ws.column_dimensions[c.column_letter].width = w
        for i, row in enumerate(rows, 2):
            for j, v in enumerate(row, 1):
                c = ws.cell(i, j, v)
                c.font, c.border, c.alignment = Font(name="Calibri"), border, Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    ws = wb.active
    ws.title = "Reponses"
    sheet(ws, ["Scénario", "Tour", "Message du candidat", "Comportement attendu", "Réponse du chat", "Latence (s)",
               "Messages en mémoire", "Profil enregistré", "Message de secours"],
          [10, 6, 38, 40, 70, 10, 11, 40, 10],
          [[r["scenario"], r["tour"], r["message"], r["attendu"], r["reponse"], r["latence_s"], r["taille_contexte"],
            json.dumps(r["profil"], ensure_ascii=False), "oui" if r["secours"] else "non"] for r in results])
    sheet(wb.create_sheet("Controles"), ["Scénario", "Tour", "Contrôle automatique", "Résultat"], [10, 6, 55, 12],
          [[c["scenario"], c["tour"], c["controle"], "Réussi" if c["reussi"] else "Échoué"] for c in checks])
    rows = []
    for sid in sorted({r["scenario"] for r in results}):
        cs = [c for c in checks if c["scenario"] == sid]
        lat = [r["latence_s"] for r in results if r["scenario"] == sid]
        rows.append([sid, f"{sum(c['reussi'] for c in cs)} / {len(cs)}", round(sum(lat) / len(lat), 1)])
    sheet(wb.create_sheet("Synthese"), ["Scénario", "Contrôles réussis", "Latence moyenne (s)"], [10, 18, 20], rows)
    wb.save(OUT_DIR / "SA-38_resultats_dialogues.xlsx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="*", help="ex. MT-01 MT-04 (par défaut : les 5 scénarios)")
    ap.add_argument("--reevaluer", action="store_true",
                    help="recalcule les contrôles à partir du dernier fichier JSON, sans rappeler le chat")
    args = ap.parse_args()
    if args.reevaluer:
        results = json.loads((OUT_DIR / "SA-38_resultats_dialogues.json").read_text(encoding="utf-8"))["reponses"]
    else:
        results = run(set(args.scenarios or []))
    checks = evaluate(results)
    save(results, checks)
    ok = sum(c["reussi"] for c in checks)
    print(f"\nContrôles réussis : {ok} / {len(checks)} -> {OUT_DIR / 'SA-38_resultats_dialogues.xlsx'}")


if __name__ == "__main__":
    main()
