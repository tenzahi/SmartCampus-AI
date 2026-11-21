"""seed demonstration data

Revision ID: 086731756304
Revises: e9f8652d7717
Create Date: 2026-11-15
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "086731756304"
down_revision: Union[str, Sequence[str], None] = "e9f8652d7717"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # 1. SPECIALITES
    # ============================================================

    op.execute("""
        INSERT INTO specialites
            (programme_id, nom, code, description)
        SELECT id, 'Développement logiciel', 'DEV', 
               'Spécialité orientée développement logiciel et applications.'
        FROM programmes
        WHERE nom = 'Licence Informatique (démo)'
          AND etablissement = 'IIT'
        ON CONFLICT (nom, programme_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO specialites
            (programme_id, nom, code, description)
        SELECT id, 'Data Science et IA', 'DSIA',
               'Spécialité orientée données, intelligence artificielle et machine learning.'
        FROM programmes
        WHERE nom = 'Licence Informatique (démo)'
          AND etablissement = 'IIT'
        ON CONFLICT (nom, programme_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO specialites
            (programme_id, nom, code, description)
        SELECT id, 'Systèmes et Réseaux', 'SR',
               'Spécialité orientée systèmes informatiques, réseaux et infrastructures.'
        FROM programmes
        WHERE nom = 'Cycle ingénieur (démo)'
          AND etablissement = 'IIT'
        ON CONFLICT (nom, programme_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO specialites
            (programme_id, nom, code, description)
        SELECT id, 'Informatique de gestion', 'IG',
               'Spécialité orientée systèmes d''information et gestion.'
        FROM programmes
        WHERE nom = 'Formation ISB (démo)'
          AND etablissement = 'ISB'
        ON CONFLICT (nom, programme_id) DO NOTHING
    """)

    # ============================================================
    # 2. PROGRAMMES PEDAGOGIQUES
    # ============================================================

    op.execute("""
        INSERT INTO programmes_pedagogiques
            (
                programme_id,
                specialite_id,
                nom,
                annee_academique,
                niveau_etude,
                description
            )
        SELECT
            p.id,
            s.id,
            'Licence Informatique - 1ère année',
            '2026-2027',
            'L1',
            'Programme pédagogique de première année en informatique.'
        FROM programmes p
        JOIN specialites s
            ON s.programme_id = p.id
        WHERE p.nom = 'Licence Informatique (démo)'
          AND p.etablissement = 'IIT'
          AND s.code = 'DEV'
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO programmes_pedagogiques
            (
                programme_id,
                specialite_id,
                nom,
                annee_academique,
                niveau_etude,
                description
            )
        SELECT
            p.id,
            s.id,
            'Licence Informatique - 2ème année',
            '2026-2027',
            'L2',
            'Programme pédagogique de deuxième année en informatique.'
        FROM programmes p
        JOIN specialites s
            ON s.programme_id = p.id
        WHERE p.nom = 'Licence Informatique (démo)'
          AND p.etablissement = 'IIT'
          AND s.code = 'DSIA'
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO programmes_pedagogiques
            (
                programme_id,
                specialite_id,
                nom,
                annee_academique,
                niveau_etude,
                description
            )
        SELECT
            p.id,
            s.id,
            'Cycle ingénieur - 1ère année',
            '2026-2027',
            'ING1',
            'Programme pédagogique de première année du cycle ingénieur.'
        FROM programmes p
        JOIN specialites s
            ON s.programme_id = p.id
        WHERE p.nom = 'Cycle ingénieur (démo)'
          AND p.etablissement = 'IIT'
          AND s.code = 'SR'
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO programmes_pedagogiques
            (
                programme_id,
                specialite_id,
                nom,
                annee_academique,
                niveau_etude,
                description
            )
        SELECT
            p.id,
            s.id,
            'Informatique de gestion - 1ère année',
            '2026-2027',
            'L1',
            'Programme pédagogique de première année en informatique de gestion.'
        FROM programmes p
        JOIN specialites s
            ON s.programme_id = p.id
        WHERE p.nom = 'Formation ISB (démo)'
          AND p.etablissement = 'ISB'
          AND s.code = 'IG'
        ON CONFLICT DO NOTHING
    """)

    # ============================================================
    # 3. MATIERES
    # ============================================================

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Programmation Python',
            'PYTHON',
            'Introduction à la programmation avec Python.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Licence Informatique - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Bases de données',
            'BDD',
            'Conception et manipulation des bases de données relationnelles.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Licence Informatique - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Algorithmique',
            'ALGO',
            'Algorithmique et structures de données.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Licence Informatique - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Intelligence artificielle',
            'IA',
            'Introduction aux concepts fondamentaux de l''intelligence artificielle.',
            2,
            2.50,
            50.00,
            6
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Licence Informatique - 2ème année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Machine Learning',
            'ML',
            'Introduction aux méthodes d''apprentissage automatique.',
            2,
            2.50,
            50.00,
            6
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Licence Informatique - 2ème année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Réseaux informatiques',
            'RESEAUX',
            'Fondamentaux des réseaux informatiques.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Cycle ingénieur - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Systèmes d''exploitation',
            'OS',
            'Principes des systèmes d''exploitation.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Cycle ingénieur - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    op.execute("""
        INSERT INTO matieres
            (
                programme_pedagogique_id,
                nom,
                code,
                description,
                semestre,
                coefficient,
                volume_horaire,
                credits
            )
        SELECT
            pp.id,
            'Systèmes d''information',
            'SI',
            'Introduction aux systèmes d''information.',
            1,
            2.00,
            45.00,
            5
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Informatique de gestion - 1ère année'
          AND pp.annee_academique = '2026-2027'
        ON CONFLICT (code, programme_pedagogique_id) DO NOTHING
    """)

    # ============================================================
    # 4. PRE-REQUIS
    # ============================================================

    op.execute("""
        INSERT INTO pre_requis
            (matiere_id, matiere_requise_id, description)
        SELECT
            m.id,
            r.id,
            'Algorithmique recommandée avant le module d''IA.'
        FROM matieres m
        JOIN matieres r
            ON r.code = 'ALGO'
        JOIN programmes_pedagogiques pp
            ON pp.id = m.programme_pedagogique_id
        JOIN programmes_pedagogiques pp_r
            ON pp_r.id = r.programme_pedagogique_id
        WHERE m.code = 'IA'
          AND pp.annee_academique = '2026-2027'
          AND pp_r.annee_academique = '2026-2027'
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        INSERT INTO pre_requis
            (matiere_id, matiere_requise_id, description)
        SELECT
            m.id,
            r.id,
            'Bases de données recommandées avant les systèmes d''information.'
        FROM matieres m
        JOIN matieres r
            ON r.code = 'BDD'
        WHERE m.code = 'SI'
        ON CONFLICT DO NOTHING
    """)

    # ============================================================
    # 5. CONDITIONS D'ADMISSION
    # ============================================================

    op.execute("""
        INSERT INTO conditions_admission
            (
                programme_id,
                programme_pedagogique_id,
                type_condition,
                description,
                valeur,
                obligatoire
            )
        SELECT
            p.id,
            NULL,
            'diplome',
            'Être titulaire du baccalauréat ou d''un diplôme équivalent.',
            'Baccalauréat',
            TRUE
        FROM programmes p
        WHERE p.nom = 'Licence Informatique (démo)'
          AND p.etablissement = 'IIT'
    """)

    op.execute("""
        INSERT INTO conditions_admission
            (
                programme_id,
                programme_pedagogique_id,
                type_condition,
                description,
                valeur,
                obligatoire
            )
        SELECT
            NULL,
            pp.id,
            'niveau',
            'Niveau académique requis pour accéder au programme pédagogique.',
            'Bac+2',
            TRUE
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Cycle ingénieur - 1ère année'
          AND pp.annee_academique = '2026-2027'
    """)

    op.execute("""
        INSERT INTO conditions_admission
            (
                programme_id,
                programme_pedagogique_id,
                type_condition,
                description,
                valeur,
                obligatoire
            )
        SELECT
            p.id,
            NULL,
            'selection',
            'Admission soumise aux conditions de sélection de l''établissement.',
            'Dossier',
            TRUE
        FROM programmes p
        WHERE p.nom = 'Formation ISB (démo)'
          AND p.etablissement = 'ISB'
    """)

    # ============================================================
    # 6. TARIFS
    # ============================================================

    op.execute("""
        INSERT INTO tarifs
            (
                programme_id,
                programme_pedagogique_id,
                montant,
                devise,
                type_frais,
                description,
                annee_academique
            )
        SELECT
            p.id,
            NULL,
            4500.00,
            'TND',
            'inscription',
            'Frais annuels de démonstration pour la licence informatique.',
            '2026-2027'
        FROM programmes p
        WHERE p.nom = 'Licence Informatique (démo)'
          AND p.etablissement = 'IIT'
    """)

    op.execute("""
        INSERT INTO tarifs
            (
                programme_id,
                programme_pedagogique_id,
                montant,
                devise,
                type_frais,
                description,
                annee_academique
            )
        SELECT
            NULL,
            pp.id,
            5200.00,
            'TND',
            'scolarite',
            'Frais de scolarité de démonstration pour le cycle ingénieur.',
            '2026-2027'
        FROM programmes_pedagogiques pp
        WHERE pp.nom = 'Cycle ingénieur - 1ère année'
          AND pp.annee_academique = '2026-2027'
    """)

    op.execute("""
        INSERT INTO tarifs
            (
                programme_id,
                programme_pedagogique_id,
                montant,
                devise,
                type_frais,
                description,
                annee_academique
            )
        SELECT
            p.id,
            NULL,
            4000.00,
            'TND',
            'scolarite',
            'Frais de scolarité de démonstration pour la formation ISB.',
            '2026-2027'
        FROM programmes p
        WHERE p.nom = 'Formation ISB (démo)'
          AND p.etablissement = 'ISB'
    """)


def downgrade() -> None:
    # Suppression des données de démonstration uniquement.
    op.execute("""
        DELETE FROM pre_requis
        WHERE description IN (
            'Algorithmique recommandée avant le module d''IA.',
            'Bases de données recommandées avant les systèmes d''information.'
        )
    """)

    op.execute("""
        DELETE FROM conditions_admission
        WHERE valeur IN ('Baccalauréat', 'Bac+2', 'Dossier')
    """)

    op.execute("""
        DELETE FROM tarifs
        WHERE annee_academique = '2026-2027'
          AND description IN (
              'Frais annuels de démonstration pour la licence informatique.',
              'Frais de scolarité de démonstration pour le cycle ingénieur.',
              'Frais de scolarité de démonstration pour la formation ISB.'
          )
    """)

    op.execute("""
        DELETE FROM matieres
        WHERE code IN (
            'PYTHON',
            'BDD',
            'ALGO',
            'IA',
            'ML',
            'RESEAUX',
            'OS',
            'SI'
        )
    """)

    op.execute("""
        DELETE FROM programmes_pedagogiques
        WHERE nom IN (
            'Licence Informatique - 1ère année',
            'Licence Informatique - 2ème année',
            'Cycle ingénieur - 1ère année',
            'Informatique de gestion - 1ère année'
        )
    """)

    op.execute("""
        DELETE FROM specialites
        WHERE code IN ('DEV', 'DSIA', 'SR', 'IG')
    """)