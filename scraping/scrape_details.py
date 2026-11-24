import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


INPUT_FILE = Path("scraping/data/formations_iit.json")
OUTPUT_FILE = Path("scraping/data/formations_iit_details.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/158.0 Safari/537.36"
    )
}


def clean(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def get_lines(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    lines = []

    for line in soup.get_text("\n", strip=True).splitlines():
        line = clean(line)

        if line:
            lines.append(line)

    return lines


def find_exact(lines, text, start=0):
    text = text.lower().strip()

    for i in range(start, len(lines)):
        if lines[i].lower().strip() == text:
            return i

    return -1


def find_contains(lines, text, start=0):
    text = text.lower().strip()

    for i in range(start, len(lines)):
        if text in lines[i].lower():
            return i

    return -1


def first_content_index(lines, formation_name):
    """
    Repère le vrai début de la fiche formation.

    Structure typique :

    CONTACT
    Formation
    Nom formation
    ...
    """

    name = formation_name.lower().strip()

    for i in range(len(lines) - 2):

        if (
            lines[i].lower().strip() == "contact"
            and lines[i + 1].lower().strip() == "formation"
            and name in lines[i + 2].lower()
        ):
            return i + 2

    # Fallback
    for i, line in enumerate(lines):

        if (
            i > 35
            and name in line.lower()
        ):
            return i

    return -1


def extract_between(lines, start, stop_indexes):
    """
    Extrait les lignes entre start et le premier arrêt.
    """

    if start < 0:
        return ""

    end = len(lines)

    for index in stop_indexes:
        if index != -1 and index > start:
            end = min(end, index)

    values = lines[start:end]

    return clean("\n".join(values))


def extract_general_information(lines, formation_index):
    """
    Extrait la description située entre le nom de la formation
    et Pré-requis / Frais / Contact / sections pédagogiques.
    """

    if formation_index == -1:
        return ""

    name = lines[formation_index].lower().strip()

    # Certains sites ont :
    #
    # Formation
    # Nom
    # Description
    #
    # D'autres :
    #
    # Formation
    # Nom
    # Nom
    # Description

    start = formation_index + 1

    # Si le nom apparaît une deuxième fois juste après
    if (
        start < len(lines)
        and lines[start].lower().strip() == name
    ):
        start += 1

    stop_labels = [
        "pré-requis",
        "pré-réquis",
        "frais national",
        "frais international",
        "contact",
        "descriptions",
        "objectif de la formation",
        "plans d'études",
        "résultat d'apprentissage",
        "référentiel métiers",
        "débouchés professionnels",
    ]

    stop_indexes = []

    for label in stop_labels:
        index = find_exact(lines, label, start)

        if index != -1:
            stop_indexes.append(index)

    return extract_between(
        lines,
        start,
        stop_indexes
    )


def extract_value_after(lines, label):
    index = find_exact(lines, label)

    if index == -1:
        return ""

    if index + 1 >= len(lines):
        return ""

    return clean(lines[index + 1])


def extract_section(lines, label, stop_labels):
    """
    Extrait une section entre son titre et le prochain titre.
    """

    start = find_exact(lines, label)

    if start == -1:
        return ""

    start += 1

    stop_indexes = []

    for stop_label in stop_labels:

        index = find_exact(
            lines,
            stop_label,
            start
        )

        if index != -1:
            stop_indexes.append(index)

    return extract_between(
        lines,
        start,
        stop_indexes
    )


def extract_organisation(lines):
    organisation = find_exact(
        lines,
        "Organisation"
    )

    if organisation == -1:
        return ""

    start = organisation + 1

    # Architecture :
    #
    # Organisation
    # du diplôme
    #
    if (
        start < len(lines)
        and lines[start].lower().strip() == "du diplôme"
    ):
        start += 1

    stop_labels = [
        "pré-requis",
        "pré-réquis",
        "frais national",
        "frais international",
        "contact",
        "objectif de la formation",
        "plans d'études",
        "résultat d'apprentissage",
        "référentiel métiers",
        "débouchés professionnels",
        "pour informations:",
    ]

    stop_indexes = []

    for label in stop_labels:

        index = find_exact(
            lines,
            label,
            start
        )

        if index != -1:
            stop_indexes.append(index)

    return extract_between(
        lines,
        start,
        stop_indexes
    )


def extract_objectifs(lines):
    return extract_section(
        lines,
        "Objectif de la formation",
        [
            "Plans d'études",
            "Résultat d'apprentissage",
            "Référentiel métiers",
            "Débouchés professionnels",
            "Contact",
        ]
    )


def extract_plans(lines):
    result = extract_section(
        lines,
        "Plans d'études",
        [
            "Résultat d'apprentissage",
            "Référentiel métiers",
            "Débouchés professionnels",
            "Contact",
        ]
    )

    if result.startswith("Principaux modules :"):
        result = result[len("Principaux modules :"):].strip()

    return result


def extract_resultats(lines):
    return extract_section(
        lines,
        "Résultat d'apprentissage",
        [
            "Référentiel métiers",
            "Débouchés professionnels",
            "Contact",
        ]
    )


def extract_debouches(lines):
    index = find_exact(
        lines,
        "Débouchés professionnels"
    )

    if index == -1:
        return ""

    stop_labels = [
        "pour informations:",
        "contact",
        "institut international de technologie",
        "copyright",
    ]

    stop_indexes = []

    for label in stop_labels:

        stop = find_exact(
            lines,
            label,
            index + 1
        )

        if stop != -1:
            stop_indexes.append(stop)

    return extract_between(
        lines,
        index + 1,
        stop_indexes
    )


def extract_conditions(lines):
    """
    Les conditions d'admission sont généralement dans le texte
    situé entre la partie admission et les frais/contact.

    On cherche les phrases caractéristiques plutôt que le menu
    ADMISSION de la navigation.
    """

    patterns = [
        "Les candidats souhaitant",
        "Accessible aux titulaires",
        "doivent impérativement",
        "Admission",
    ]

    start = -1

    for pattern in patterns:

        index = find_contains(
            lines,
            pattern,
            40
        )

        if index != -1:
            start = index
            break

    if start == -1:
        return ""

    stop_labels = [
        "frais national",
        "frais international",
        "contact",
        "pour informations:",
        "institut international de technologie",
        "copyright",
    ]

    stop_indexes = []

    for label in stop_labels:

        stop = find_exact(
            lines,
            label,
            start + 1
        )

        if stop != -1:
            stop_indexes.append(stop)

    result = extract_between(
        lines,
        start,
        stop_indexes
    )

    return result


def extract_specialites(lines):
    """
    On ne crée une spécialité que si elle est explicitement
    identifiable dans la fiche.
    """

    specialites = []

    known = {
        "génie logiciel et systèmes intelligents": "GLSI",
        "architecture": "ARCH",
        "systèmes de données et intelligence artificielle": "SDIA",
        "analyse de données et intelligence artificielle": "ADIA",
    }

    for name, code in known.items():

        index = find_contains(
            lines,
            name,
            40
        )

        if index != -1:

            value = lines[index]

            if not any(
                s["nom"].lower() == value.lower()
                for s in specialites
            ):
                specialites.append({
                    "nom": value,
                    "code": code
                })

    return specialites


def extract_formation(item):

    nom = item.get("nom", "")
    url = item.get("url", "")

    result = {
        "nom": nom,
        "url": url,
        "etablissement": item.get(
            "etablissement",
            "IIT"
        ),
        "source": item.get("source", ""),
        "page_detail_disponible": False,

        "langue_formation": "",
        "prerequis": "",
        "frais_national": "",
        "frais_international": "",

        "description": "",
        "organisation_diplome": "",
        "objectifs": "",

        "specialites": [],

        "plans_etudes": "",
        "resultats_apprentissage": "",
        "debouches": "",

        "conditions_admission_detaillees": "",
    }

    # https://iit.tn n'est pas une fiche formation
    if (
        not url
        or url == "#"
        or url.rstrip("/") == "https://iit.tn"
    ):
        print("   PAGE DETAIL IGNORÉE")
        return result

    try:

        lines = get_lines(url)

        result["page_detail_disponible"] = True

        formation_index = first_content_index(
            lines,
            nom
        )

        result["description"] = extract_general_information(
            lines,
            formation_index
        )

        result["prerequis"] = extract_value_after(
            lines,
            "Pré-requis"
        )

        if not result["prerequis"]:
            result["prerequis"] = extract_value_after(
                lines,
                "Pré-Réquis"
            )

        result["frais_national"] = extract_value_after(
            lines,
            "Frais national"
        )

        result["frais_international"] = extract_value_after(
            lines,
            "Frais international"
        )

        result["organisation_diplome"] = extract_organisation(
            lines
        )

        result["objectifs"] = extract_objectifs(
            lines
        )

        result["plans_etudes"] = extract_plans(
            lines
        )

        result["resultats_apprentissage"] = extract_resultats(
            lines
        )

        result["debouches"] = extract_debouches(
            lines
        )

        result["conditions_admission_detaillees"] = extract_conditions(
            lines
        )

        result["specialites"] = extract_specialites(
            lines
        )

        return result

    except Exception as e:

        print(f"   ERREUR : {e}")

        result["page_detail_disponible"] = False

        return result


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        formations = json.load(f)

    results = []

    print()
    print("=" * 70)
    print("SCRAPING DES DETAILS IIT")
    print("=" * 70)

    for i, formation in enumerate(
        formations,
        start=1
    ):

        print()
        print(
            f"[{i}/{len(formations)}] "
            f"{formation.get('nom', '')}"
        )

        print(
            f"URL : "
            f"{formation.get('url', '')}"
        )

        result = extract_formation(
            formation
        )

        results.append(result)

        if result["page_detail_disponible"]:

            print("   OK")

            fields = [
                ("Prérequis", "prerequis"),
                ("Frais national", "frais_national"),
                ("Frais étranger", "frais_international"),
                ("Description", "description"),
                ("Organisation", "organisation_diplome"),
                ("Objectifs", "objectifs"),
                ("Plans", "plans_etudes"),
                ("Résultats", "resultats_apprentissage"),
                ("Débouchés", "debouches"),
                ("Conditions", "conditions_admission_detaillees"),
            ]

            for label, key in fields:

                status = (
                    "OK"
                    if result[key]
                    else "VIDE"
                )

                print(
                    f"   {label:<18}: {status}"
                )

        time.sleep(0.5)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print("SCRAPING TERMINE")
    print("=" * 70)
    print(
        f"Fichier : {OUTPUT_FILE}"
    )
    print(
        f"Formations traitées : "
        f"{len(results)}"
    )


if __name__ == "__main__":
    main()