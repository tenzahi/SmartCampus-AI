"""Extraction du profil du candidat à partir de ses messages (SA-37).

Le profil (section du bac, moyenne, centres d'intérêt, préférence, langue) est
mis à jour à chaque message et envoyé au modèle. Ainsi, le modèle se souvient
de ces informations même quand les premiers messages sortent de la mémoire
récente (10 derniers messages).

L'extraction utilise des règles simples plutôt qu'un appel au modèle : sur la
machine de test, un appel supplémentaire doublerait le temps de réponse.
"""
import re

# Un nombre isolé : les chiffres de l'Arabizi (« mta3i », « 9olli ») ne sont pas des notes
NUMBER = r"(?<![A-Za-zÀ-ÿ\d])(\d{1,2}(?:[.,]\d{1,2})?)(?![A-Za-zÀ-ÿ\d])"

# Mots qui annoncent une moyenne (français, Arabizi, arabe)
MOYENNE_KEYWORDS = re.compile(r"moyenne|moyen\b|m3adel|ma3adel|معدّل|معدل|المعدّل|المعدل|\bnote\b", re.I)

# « 14.5 mchi 13 », « 14,5 et non 13 », « 14.5 au lieu de 13 » : la première valeur est la bonne
CORRECTION_FIRST = re.compile(
    NUMBER + r"\s*(?:/\s*20\s*)?(?:mchi|mich|machi|mouch|moch|pas|et non|au lieu de|موش|مش|ماشي)\s+" + NUMBER, re.I)
# « pas 13 mais 14,5 » : la seconde valeur est la bonne
CORRECTION_SECOND = re.compile(r"(?:pas|mchi|mouch|موش)\s+" + NUMBER + r"\s*(?:/\s*20\s*)?(?:mais|ama|اما|أما)\s+" + NUMBER, re.I)
OVER_20 = re.compile(NUMBER + r"\s*/\s*20")

# Section du bac : cherchée juste après « bac », « terminale », « باك »…
BAC_KEYWORDS = re.compile(r"\bbac\b|baccalaur[ée]at|terminale|الباك|باك|البكالوريا|بكالوريا", re.I)
BAC_WINDOW = 35
BAC_SECTIONS = [
    (re.compile(r"sciences? exp|exp[ée]rimentales?|علوم تجريبية", re.I), "Sciences expérimentales"),
    (re.compile(r"\bmaths?\b|math[ée]matiques?|رياضيات", re.I), "Mathématiques"),
    (re.compile(r"\binfo\b|informatique|إعلامية|اعلامية", re.I), "Sciences de l'informatique"),
    (re.compile(r"technique|تقنية", re.I), "Technique"),
    (re.compile(r"\beco\b|[ée]conomie|gestion|اقتصاد", re.I), "Économie et gestion"),
    (re.compile(r"lettres?|آداب", re.I), "Lettres"),
    (re.compile(r"\bsport\b|رياضة", re.I), "Sport"),
    (re.compile(r"\bsciences?\b|علوم", re.I), "Sciences"),
]

INTERESTS = [
    (re.compile(r"d[ée]veloppement web|\bweb\b", re.I), "développement web"),
    (re.compile(r"intelligence artificielle|\bia\b|الذكاء الاصطناعي|ذكاء اصطناعي", re.I), "intelligence artificielle"),
    (re.compile(r"cyber", re.I), "cybersécurité"),
    (re.compile(r"r[ée]seaux?|شبكات", re.I), "réseaux"),
    (re.compile(r"informatique|programmation|برمجة|الإعلامية", re.I), "informatique"),
    (re.compile(r"\bdata\b|science des donn[ée]es", re.I), "données"),
    (re.compile(r"robot", re.I), "robotique"),
    (re.compile(r"m[ée]canique", re.I), "mécanique"),
    (re.compile(r"[ée]lectri|[ée]lectronique", re.I), "électricité et électronique"),
    (re.compile(r"g[ée]nie civil|b[âa]timent", re.I), "génie civil"),
    (re.compile(r"gestion|business|management|marketing|commerce", re.I), "gestion et business"),
    (re.compile(r"\bmaths?\b|math[ée]matiques|رياضيات", re.I), "mathématiques"),
    (re.compile(r"physique|فيزياء", re.I), "physique"),
    (re.compile(r"biolog|بيولوجيا", re.I), "biologie"),
    (re.compile(r"sant[ée]|m[ée]dical|صحي", re.I), "santé"),
]

ARABIC_LETTER = re.compile(r"[؀-ۿ]")
LATIN_LETTER = re.compile(r"[A-Za-zÀ-ÿ]")
ARABIZI_WORD = re.compile(
    r"\b[a-z]*[2-9][a-z]+\b|\b(?:ena|n7eb|nheb|chnowa|chnoua|mta3i|mte3i|behi|barcha|fel|3andi|kifech|kifach|mrigel|mchi|tnajem|w)\b", re.I)
FRENCH_WORD = re.compile(
    r"\b(?:je|j'|le|la|les|est|pour|des|une|mais|avec|bonjour|merci|quelles?|formations?|conditions|ma|mon)\b", re.I)
ENGLISH_WORD = re.compile(r"\b(?:the|please|can|you|answer|english|what|which|i|want)\b", re.I)


def _to_float(value: str) -> float:
    return float(value.replace(",", "."))


def _valid(value: float) -> bool:
    return 0 <= value <= 20


def extract_moyenne(message: str) -> float | None:
    """Renvoie la moyenne citée dans le message, en tenant compte des corrections."""
    for pattern, index in ((CORRECTION_SECOND, 2), (CORRECTION_FIRST, 1)):
        m = pattern.search(message)
        if m and _valid(_to_float(m.group(index))):
            return _to_float(m.group(index))
    m = OVER_20.search(message)
    if m and _valid(_to_float(m.group(1))):
        return _to_float(m.group(1))
    keyword = MOYENNE_KEYWORDS.search(message)
    if not keyword:
        return None
    # Le premier nombre après le mot « moyenne », sinon le premier nombre du message
    for part in (message[keyword.end():], message):
        for m in re.finditer(NUMBER, part):
            value = _to_float(m.group(1))
            if _valid(value):
                return value
    return None


def _bac_windows(message: str) -> list[tuple[int, int]]:
    """Passages « bac … » : du mot « bac » jusqu'à la ponctuation suivante (35 caractères au plus)."""
    windows = []
    for m in BAC_KEYWORDS.finditer(message):
        end = min(len(message), m.end() + BAC_WINDOW)
        stop = re.search(r"[,.;:!?،؟]", message[m.end():end])
        windows.append((m.start(), m.end() + stop.start() if stop else end))
    return windows


def extract_bac_section(message: str) -> str | None:
    for start, end in _bac_windows(message):
        window = message[start:end]
        best = None
        for pattern, label in BAC_SECTIONS:
            m = pattern.search(window)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), label)
        if best:
            return best[1]
    return None


def extract_interests(message: str) -> list[str]:
    # On ignore la section du bac (« bac eco w gestion » n'est pas un centre d'intérêt)
    text = message
    for start, end in _bac_windows(message):
        text = text[:start] + " " * (end - start) + text[end:]
    return [label for pattern, label in INTERESTS if pattern.search(text)]


def extract_preference(message: str) -> str | None:
    if re.search(r"pratique|stage", message, re.I):
        return "formation pratique"
    if re.search(r"th[ée]orique", message, re.I) and not re.search(r"ma\s+n7ebe?ch|n'aime pas|pas\s+th[ée]orique", message, re.I):
        return "formation théorique"
    return None


def detect_language(message: str) -> str | None:
    arabic = len(ARABIC_LETTER.findall(message))
    latin = len(LATIN_LETTER.findall(message))
    if arabic + latin == 0:
        return None
    if arabic > latin:
        return "tunisien (écriture arabe)"
    arabizi = len(ARABIZI_WORD.findall(message))
    french = len(FRENCH_WORD.findall(message))
    if arabizi and french:
        return "mélange français et dialecte"
    if arabizi:
        return "Arabizi"
    if len(ENGLISH_WORD.findall(message)) >= 2 and french == 0:
        return "anglais"
    return "français"


def extract_profile_updates(message: str) -> dict:
    """Informations du profil trouvées dans un message du candidat."""
    updates = {}
    if (section := extract_bac_section(message)):
        updates["bac_section"] = section
    if (moyenne := extract_moyenne(message)) is not None:
        updates["moyenne"] = moyenne
    if (interests := extract_interests(message)):
        updates["interets"] = interests
    if (preference := extract_preference(message)):
        updates["preference"] = preference
    if (langue := detect_language(message)):
        updates["langue"] = langue
    return updates


def merge_profile(profile: dict, updates: dict) -> dict:
    """Fusionne les nouvelles informations : les centres d'intérêt s'ajoutent, le reste est remplacé."""
    merged = dict(profile)
    for key, value in updates.items():
        if key == "interets":
            merged["interets"] = list(dict.fromkeys(merged.get("interets", []) + value))
        else:
            merged[key] = value
    return merged


def format_profile(profile: dict) -> str:
    """Résumé du profil ajouté aux consignes du modèle (vide si rien n'est connu)."""
    lines = []
    if profile.get("bac_section"):
        lines.append(f"- Section du bac : {profile['bac_section']}")
    if profile.get("moyenne") is not None:
        lines.append(f"- Moyenne : {profile['moyenne']:g}/20".replace(".", ","))
    if profile.get("interets"):
        lines.append(f"- Centres d'intérêt : {', '.join(profile['interets'])}")
    if profile.get("preference"):
        lines.append(f"- Préférence : {profile['preference']}")
    if profile.get("langue"):
        lines.append(f"- Langue de son dernier message : {profile['langue']}")
    if not lines:
        return ""
    return ("Profil du candidat retenu pendant la conversation. Utilise-le pour personnaliser ta réponse "
            "sans le répéter mot pour mot. Si le candidat corrige une information, c'est la dernière valeur qui compte.\n"
            + "\n".join(lines))
