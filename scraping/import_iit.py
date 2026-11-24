import json
import re
import subprocess


JSON_FILE = "data/formations_iit_details.json"

# Convention utilisée pour le projet
ANNEE_ACADEMIQUE = "2026-2027"


def sql_escape(value):
    """
    Protège une chaîne avant de l'envoyer à PostgreSQL.
    """
    if value is None:
        return ""

    return str(value).replace("'", "''")


def run_sql(sql):
    """
    Exécute une commande SQL dans le conteneur PostgreSQL.
    """

    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "smartcampus",
        "-d",
        "smartcampus",
        "-c",
        sql,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        print()
        print("ERREUR SQL :")
        print(result.stderr)
        raise SystemExit(1)

    return result.stdout


def extract_first_integer(output):
    """
    Extrait le premier entier isolé dans la sortie de psql.

    Exemple :

     id
    ----
     18
    (1 row)

    retourne 18.
    """

    for line in output.splitlines():

        line = line.strip()

        if line.isdigit():
            return int(line)

    return None


def parse_money(value):
    """
    Transforme :

        776DT/9 mois* -> 776.0
        278€/9 mois*  -> 278.0

    """

    if not value:
        return None

    match = re.search(
        r"([\d\s]+(?:[.,]\d+)?)",
        value
    )

    if not match:
        return None

    number = match.group(1)

    number = (
        number
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        return float(number)
    except ValueError:
        return None


def get_level(nom):
    """
    Détermine le niveau de la formation.
    """

    nom_lower = nom.lower()

    if "architecture" in nom_lower:
        return "Ingénierie"

    if nom_lower.startswith("licence"):
        return "Licence"

    if "réseaux" in nom_lower:
        return "Licence"

    if "systèmes embarqués" in nom_lower:
        return "Licence"

    if "big data" in nom_lower:
        return "Licence"

    if "génie logiciel" in nom_lower:
        return "Ingénierie"

    if "génie" in nom_lower:
        return "Ingénierie"

    return "Licence"


def find_programme_id(nom):
    """
    Recherche un programme IIT existant.

    Si le programme existe déjà, son ID est retourné.
    Sinon None.
    """

    sql = f"""
    SELECT id
    FROM programmes
    WHERE etablissement = 'IIT'
      AND nom = '{sql_escape(nom)}'
    LIMIT 1;
    """

    output = run_sql(sql)

    programme_id = extract_first_integer(output)

    return programme_id


def insert_programme(data):
    """
    Récupère le programme existant ou le crée.
    """

    nom = data["nom"]

    # -------------------------------------------------
    # 1. Vérifier si le programme existe déjà
    # -------------------------------------------------

    programme_id = find_programme_id(nom)

    if programme_id is not None:

        print(
            f"   Programme existant : "
            f"{nom} (id={programme_id})"
        )

        return programme_id

    # -------------------------------------------------
    # 2. Créer le programme
    # -------------------------------------------------

    niveau = get_level(nom)

    sql = f"""
    INSERT INTO programmes
        (
            etablissement,
            nom,
            niveau
        )
    VALUES
        (
            'IIT',
            '{sql_escape(nom)}',
            '{sql_escape(niveau)}'
        )
    RETURNING id;
    """

    output = run_sql(sql)

    programme_id = extract_first_integer(output)

    if programme_id is None:

        print()
        print("Impossible de récupérer l'ID du programme.")
        print("Sortie PostgreSQL :")
        print(output)

        raise SystemExit(1)

    print(
        f"   Programme créé : "
        f"{nom} (id={programme_id})"
    )

    return programme_id


def find_programme_pedagogique(
    programme_id,
    nom
):
    """
    Vérifie si le programme pédagogique existe déjà.
    """

    pp_name = f"{nom} - {ANNEE_ACADEMIQUE}"

    sql = f"""
    SELECT id
    FROM programmes_pedagogiques
    WHERE programme_id = {programme_id}
      AND nom = '{sql_escape(pp_name)}'
      AND annee_academique = '{ANNEE_ACADEMIQUE}'
    LIMIT 1;
    """

    output = run_sql(sql)

    return extract_first_integer(output)


def insert_programme_pedagogique(
    programme_id,
    data
):
    """
    Crée un programme pédagogique à partir
    des informations récupérées sur IIT.
    """

    nom = data["nom"]

    existing_id = find_programme_pedagogique(
        programme_id,
        nom
    )

    if existing_id is not None:

        print(
            f"   Programme pédagogique existant "
            f"(id={existing_id})"
        )

        return existing_id

    # -------------------------------------------------
    # Construire la description
    # -------------------------------------------------

    description_parts = []

    if data.get("description"):

        description_parts.append(
            data["description"]
        )

    if data.get("objectifs"):

        description_parts.append(
            "Objectifs :\n"
            + data["objectifs"]
        )

    if data.get("organisation_diplome"):

        description_parts.append(
            "Organisation du diplôme :\n"
            + data["organisation_diplome"]
        )

    if data.get("plans_etudes"):

        description_parts.append(
            "Plans d'études :\n"
            + data["plans_etudes"]
        )

    description = "\n\n".join(
        description_parts
    )

    pp_name = (
        f"{nom} - "
        f"{ANNEE_ACADEMIQUE}"
    )

    niveau = get_level(nom)

    sql = f"""
    INSERT INTO programmes_pedagogiques
        (
            programme_id,
            specialite_id,
            nom,
            annee_academique,
            niveau_etude,
            description,
            actif
        )
    VALUES
        (
            {programme_id},
            NULL,
            '{sql_escape(pp_name)}',
            '{ANNEE_ACADEMIQUE}',
            '{sql_escape(niveau)}',
            '{sql_escape(description)}',
            TRUE
        )
    RETURNING id;
    """

    output = run_sql(sql)

    pp_id = extract_first_integer(output)

    if pp_id is None:

        print(
            "   Impossible de récupérer "
            "l'ID du programme pédagogique."
        )

        print(output)

        raise SystemExit(1)

    print(
        f"   Programme pédagogique créé "
        f"(id={pp_id})"
    )

    return pp_id


def condition_exists(
    programme_id,
    prerequis
):
    """
    Vérifie si le prérequis existe déjà.
    """

    sql = f"""
    SELECT id
    FROM conditions_admission
    WHERE programme_id = {programme_id}
      AND type_condition = 'prerequis'
      AND valeur = '{sql_escape(prerequis)}'
    LIMIT 1;
    """

    output = run_sql(sql)

    return extract_first_integer(output)


def insert_conditions(
    programme_id,
    data
):
    """
    Insère le prérequis réellement récupéré
    sur le site IIT.
    """

    prerequis = data.get(
        "prerequis",
        ""
    ).strip()

    if not prerequis:

        print(
            "   Condition d'admission : "
            "aucune donnée"
        )

        return

    existing_id = condition_exists(
        programme_id,
        prerequis
    )

    if existing_id is not None:

        print(
            f"   Condition existante "
            f"(id={existing_id})"
        )

        return

    description = (
        "Prérequis indiqué par l'IIT : "
        + prerequis
    )

    sql = f"""
    INSERT INTO conditions_admission
        (
            programme_id,
            programme_pedagogique_id,
            type_condition,
            description,
            valeur,
            obligatoire,
            actif
        )
    VALUES
        (
            {programme_id},
            NULL,
            'prerequis',
            '{sql_escape(description)}',
            '{sql_escape(prerequis)}',
            TRUE,
            TRUE
        )
    RETURNING id;
    """

    output = run_sql(sql)

    condition_id = extract_first_integer(output)

    if condition_id is None:

        print(
            "   Impossible de récupérer "
            "l'ID de la condition."
        )

        print(output)

        raise SystemExit(1)

    print(
        f"   Condition d'admission créée "
        f"(id={condition_id})"
    )


def tarif_exists(
    programme_id,
    montant,
    devise
):
    """
    Vérifie si un tarif existe déjà.
    """

    sql = f"""
    SELECT id
    FROM tarifs
    WHERE programme_id = {programme_id}
      AND montant = {montant}
      AND devise = '{devise}'
      AND annee_academique = '{ANNEE_ACADEMIQUE}'
    LIMIT 1;
    """

    output = run_sql(sql)

    return extract_first_integer(output)


def insert_tarif(
    programme_id,
    montant,
    devise,
    type_frais
):
    """
    Insère un tarif s'il n'existe pas.
    """

    if montant is None:
        return

    existing_id = tarif_exists(
        programme_id,
        montant,
        devise
    )

    if existing_id is not None:

        print(
            f"   Tarif existant : "
            f"{montant} {devise}"
        )

        return

    description = (
        "Tarif récupéré depuis le site officiel "
        "de l'IIT."
    )

    sql = f"""
    INSERT INTO tarifs
        (
            programme_id,
            programme_pedagogique_id,
            montant,
            devise,
            type_frais,
            description,
            annee_academique,
            actif
        )
    VALUES
        (
            {programme_id},
            NULL,
            {montant},
            '{devise}',
            '{sql_escape(type_frais)}',
            '{sql_escape(description)}',
            '{ANNEE_ACADEMIQUE}',
            TRUE
        )
    RETURNING id;
    """

    output = run_sql(sql)

    tarif_id = extract_first_integer(output)

    if tarif_id is None:

        print(
            "   Impossible de récupérer "
            "l'ID du tarif."
        )

        print(output)

        raise SystemExit(1)

    print(
        f"   Tarif créé : "
        f"{montant} {devise} "
        f"(id={tarif_id})"
    )


def insert_tarifs(
    programme_id,
    data
):
    """
    Insère les tarifs national et étranger.
    """

    national = parse_money(
        data.get("frais_national")
    )

    international = parse_money(
        data.get("frais_international")
    )

    # -------------------------------------------------
    # Tarif national
    # -------------------------------------------------

    if national is not None:

        insert_tarif(
            programme_id,
            national,
            "TND",
            "scolarite"
        )

    else:

        print(
            "   Tarif national : "
            "non renseigné"
        )

    # -------------------------------------------------
    # Tarif étranger
    # -------------------------------------------------

    if international is not None:

        insert_tarif(
            programme_id,
            international,
            "EUR",
            "scolarite"
        )

    else:

        print(
            "   Tarif étranger : "
            "non renseigné"
        )


def main():

    print()
    print("=" * 70)
    print("IMPORT DES DONNÉES IIT → POSTGRESQL")
    print("=" * 70)
    print()

    # -------------------------------------------------
    # Lire le JSON
    # -------------------------------------------------

    try:

        with open(
            JSON_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            formations = json.load(f)

    except FileNotFoundError:

        print(
            f"Fichier introuvable : "
            f"{JSON_FILE}"
        )

        raise SystemExit(1)

    print(
        f"Formations trouvées dans le JSON : "
        f"{len(formations)}"
    )

    total = 0
    detaillees = 0

    # -------------------------------------------------
    # Parcours des formations
    # -------------------------------------------------

    for data in formations:

        nom = data.get(
            "nom",
            ""
        ).strip()

        if not nom:
            continue

        print()
        print("-" * 70)
        print(nom)

        # -------------------------------------------------
        # Programme
        # -------------------------------------------------

        programme_id = insert_programme(
            data
        )

        total += 1

        # -------------------------------------------------
        # Pas de fiche détaillée
        # -------------------------------------------------

        if not data.get(
            "page_detail_disponible",
            False
        ):

            print(
                "   ⚠️ Fiche détaillée absente."
            )

            print(
                "   → Programme conservé uniquement."
            )

            continue

        detaillees += 1

        # -------------------------------------------------
        # Programme pédagogique
        # -------------------------------------------------

        insert_programme_pedagogique(
            programme_id,
            data
        )

        # -------------------------------------------------
        # Conditions d'admission
        # -------------------------------------------------

        insert_conditions(
            programme_id,
            data
        )

        # -------------------------------------------------
        # Tarifs
        # -------------------------------------------------

        insert_tarifs(
            programme_id,
            data
        )

    # -------------------------------------------------
    # Résumé
    # -------------------------------------------------

    print()
    print("=" * 70)
    print("IMPORT TERMINÉ")
    print("=" * 70)

    print(
        f"Programmes traités : {total}"
    )

    print(
        f"Fiches détaillées : {detaillees}"
    )

    print(
        "Aucune donnée existante "
        "n'a été supprimée."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()