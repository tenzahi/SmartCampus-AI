import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime


INPUT_FILE = "scraping/data/nau_programmes.json"
OUTPUT_FILE = "scraping/data/nau_programmes_details.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    )
}


def clean_text(text):
    """Nettoie le texte."""

    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_page(url):

    print(f"[SCRAPING] {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    # IIT utilise UTF-8
    response.encoding = "utf-8"

    return BeautifulSoup(
        response.text,
        "lxml"
    )


def remove_unwanted_elements(soup):

    for tag in soup.find_all([
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "footer",
        "form"
    ]):
        tag.decompose()


def extract_text_blocks(soup):

    """
    Récupère les blocs de texte importants :
    titres, paragraphes, listes.
    """

    blocks = []

    for element in soup.find_all([
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li"
    ]):

        text = clean_text(
            element.get_text(" ", strip=True)
        )

        if not text:
            continue

        # éviter les textes trop courts
        if len(text) < 2:
            continue

        blocks.append({
            "tag": element.name,
            "text": text
        })

    return blocks


def extract_full_text(soup):

    """
    Extrait tout le texte utile de la page.
    """

    # Chercher d'abord le contenu principal
    selectors = [
        "main",
        "article",
        ".entry-content",
        ".post-content",
        ".elementor",
        "#content",
        ".site-content"
    ]

    for selector in selectors:

        element = soup.select_one(selector)

        if element:

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if len(text) > 300:

                return text

    # fallback
    body = soup.find("body")

    if body:

        return clean_text(
            body.get_text(
                " ",
                strip=True
            )
        )

    return ""


def find_content_by_keywords(
    blocks,
    keywords
):

    """
    Cherche du contenu autour d'un titre
    contenant un mot-clé.
    """

    for i, block in enumerate(blocks):

        title = block["text"].lower()

        found = any(
            keyword.lower() in title
            for keyword in keywords
        )

        if not found:
            continue

        content = []

        # récupérer les blocs suivants
        for next_block in blocks[i + 1:]:

            # arrêter lorsqu'on rencontre
            # un nouveau titre
            if next_block["tag"] in [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6"
            ]:
                break

            content.append(
                next_block["text"]
            )

        if content:

            return " ".join(content)

    return ""


def extract_program_details(program):

    url = program["url"]

    soup = get_page(url)

    remove_unwanted_elements(soup)

    blocks = extract_text_blocks(soup)

    full_text = extract_full_text(soup)

    details = {

        "nom": program["nom"],

        "etablissement": "IIT",

        "source_url": url,

        "description": full_text,

        "prerequis": find_content_by_keywords(
            blocks,
            [
                "pré-requis",
                "prérequis",
                "pré requis",
                "conditions d'admission",
                "admission"
            ]
        ),

        "frais": find_content_by_keywords(
            blocks,
            [
                "frais",
                "frais de scolarité",
                "tarif",
                "tarifs"
            ]
        ),

        "objectifs": find_content_by_keywords(
            blocks,
            [
                "objectif",
                "objectifs",
                "objectif de la formation"
            ]
        ),

        "organisation": find_content_by_keywords(
            blocks,
            [
                "organisation",
                "organisation du diplôme",
                "durée"
            ]
        ),

        "programme": find_content_by_keywords(
            blocks,
            [
                "programme",
                "plan d'étude",
                "plans d'études",
                "plan d'études"
            ]
        ),

        "resultats_apprentissage": find_content_by_keywords(
            blocks,
            [
                "résultat d'apprentissage",
                "résultats d'apprentissage",
                "apprentissage"
            ]
        ),

        "debouches": find_content_by_keywords(
            blocks,
            [
                "référentiel métiers",
                "métiers",
                "débouchés",
                "débouchet"
            ]
        ),

        "blocs": blocks,

        "scraped_at": datetime.now().isoformat()

    }

    return details


def main():

    print()
    print("=" * 70)
    print("SMARTCAMPUS-AI - SCRAPING IIT")
    print("=" * 70)
    print()

    # Charger les formations
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        programs = json.load(file)

    print(
        f"{len(programs)} formations trouvées."
    )

    print()

    results = []

    for index, program in enumerate(
        programs,
        start=1
    ):

        print(
            f"[{index}/{len(programs)}] "
            f"{program['nom']}"
        )

        try:

            details = extract_program_details(
                program
            )

            results.append(details)

            print(
                f"   -> OK "
                f"({len(details['description'])} caractères)"
            )

        except Exception as error:

            print(
                f"   -> ERREUR : {error}"
            )

        # Petite pause pour ne pas surcharger le site
        time.sleep(1)

    # Sauvegarder
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print(
        f"[OK] {len(results)} formations récupérées"
    )
    print(
        f"[OK] {OUTPUT_FILE}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()