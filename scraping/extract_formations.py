import json

INPUT = "scraping/data/nau_raw.json"
OUTPUT = "scraping/data/formations_iit.json"

EXCLUS = {
    "Cycle Préparatoire",
    "Licence",
    "Licences Technologiques",
    "Mastère",
    "Formation continue",
}

data = json.load(open(INPUT, encoding="utf-8"))

formations = []
seen = set()

for page in data:
    for link in page.get("links", []):
        title = link.get("title", "").strip()
        url = link.get("url", "").strip()

        if not title or not url:
            continue

        if title in EXCLUS:
            continue

        if title in seen:
            continue

        # On garde uniquement les formations IIT
        if (
            title.startswith("Licence en ")
            or title in {
                "Architecture",
                "Réseaux et Cybersécurité",
                "Systèmes Embarqués & IoT",
                "Big Data et Analyse de Données",
                "Génie Logiciel et Systèmes Intelligents",
                "Génie Civil",
                "Génie des procédés",
                "Génie Informatique",
                "Génie Mécanique",
                "Génie Industriel",
            }
        ):
            formations.append({
                "nom": title,
                "url": url,
                "etablissement": "IIT",
                "source": page.get("source_url")
            })
            seen.add(title)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(formations, f, ensure_ascii=False, indent=2)

print(f"{len(formations)} formations extraites.")
for formation in formations:
    print("-", formation["nom"])