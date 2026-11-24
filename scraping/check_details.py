import json

with open(
    "scraping/data/formations_iit_details.json",
    encoding="utf-8"
) as f:
    data = json.load(f)

for x in data:
    print(
        f"{x['nom']} | "
        f"objectifs={'OK' if x.get('objectifs') else 'VIDE'} | "
        f"résultats={'OK' if x.get('resultats_apprentissage') else 'VIDE'} | "
        f"débouchés={'OK' if x.get('debouches') else 'VIDE'} | "
        f"organisation={'OK' if x.get('organisation_diplome') else 'VIDE'} | "
        f"plans={'OK' if x.get('plans_etudes') else 'VIDE'} | "
        f"spécialités={'OK' if x.get('specialites') else 'VIDE'}"
    )