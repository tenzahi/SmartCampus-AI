"""create academic catalogue tables

Revision ID: e9f8652d7717
Revises:
Create Date: 2026-11-15
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e9f8652d7717"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Specialites
    op.execute("""
        CREATE TABLE specialites (
            id SERIAL PRIMARY KEY,
            programme_id INTEGER NOT NULL,
            nom VARCHAR(150) NOT NULL,
            code VARCHAR(30) NOT NULL,
            description TEXT,
            actif BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_specialites_programme
                FOREIGN KEY (programme_id)
                REFERENCES programmes(id),

            CONSTRAINT uq_specialites_nom_programme
                UNIQUE (nom, programme_id),

            CONSTRAINT uq_specialites_id_programme
                UNIQUE (id, programme_id)
        )
    """)

    # 2. Programmes pedagogiques
    op.execute("""
        CREATE TABLE programmes_pedagogiques (
            id SERIAL PRIMARY KEY,
            programme_id INTEGER NOT NULL,
            specialite_id INTEGER,
            nom VARCHAR(150) NOT NULL,
            annee_academique VARCHAR(9) NOT NULL,
            niveau_etude VARCHAR(50) NOT NULL,
            description TEXT,
            actif BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_programmes_pedagogiques_programme
                FOREIGN KEY (programme_id)
                REFERENCES programmes(id),

            CONSTRAINT fk_programmes_pedagogiques_specialite
                FOREIGN KEY (programme_id, specialite_id)
                REFERENCES specialites(programme_id, id),

            CONSTRAINT uq_programmes_pedagogiques
                UNIQUE NULLS NOT DISTINCT
                (programme_id, specialite_id, nom, annee_academique),

            CONSTRAINT chk_programmes_pedagogiques_annee
                CHECK (annee_academique ~ '^[0-9]{4}-[0-9]{4}$')
        )
    """)

    # 3. Matieres
    op.execute("""
        CREATE TABLE matieres (
            id SERIAL PRIMARY KEY,
            programme_pedagogique_id INTEGER NOT NULL,
            nom VARCHAR(150) NOT NULL,
            code VARCHAR(30) NOT NULL,
            description TEXT,
            semestre INTEGER NOT NULL,
            coefficient NUMERIC(4,2) NOT NULL DEFAULT 1,
            volume_horaire NUMERIC(5,2) NOT NULL DEFAULT 0,
            credits INTEGER NOT NULL DEFAULT 0,
            actif BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_matieres_programme_pedagogique
                FOREIGN KEY (programme_pedagogique_id)
                REFERENCES programmes_pedagogiques(id),

            CONSTRAINT uq_matieres_code_programme
                UNIQUE (code, programme_pedagogique_id),

            CONSTRAINT chk_matieres_semestre
                CHECK (semestre BETWEEN 1 AND 12),

            CONSTRAINT chk_matieres_coefficient
                CHECK (coefficient >= 0),

            CONSTRAINT chk_matieres_volume_horaire
                CHECK (volume_horaire >= 0),

            CONSTRAINT chk_matieres_credits
                CHECK (credits >= 0)
        )
    """)

    # 4. Pre-requis
    op.execute("""
        CREATE TABLE pre_requis (
            matiere_id INTEGER NOT NULL,
            matiere_requise_id INTEGER NOT NULL,
            description TEXT,

            CONSTRAINT pk_pre_requis
                PRIMARY KEY (matiere_id, matiere_requise_id),

            CONSTRAINT fk_pre_requis_matiere
                FOREIGN KEY (matiere_id)
                REFERENCES matieres(id),

            CONSTRAINT fk_pre_requis_matiere_requise
                FOREIGN KEY (matiere_requise_id)
                REFERENCES matieres(id),

            CONSTRAINT chk_pre_requis_no_self
                CHECK (matiere_id <> matiere_requise_id)
        )
    """)

    # 5. Conditions d'admission
    op.execute("""
        CREATE TABLE conditions_admission (
            id SERIAL PRIMARY KEY,
            programme_id INTEGER,
            programme_pedagogique_id INTEGER,
            type_condition VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            valeur VARCHAR(100),
            obligatoire BOOLEAN NOT NULL DEFAULT TRUE,
            actif BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_conditions_admission_programme
                FOREIGN KEY (programme_id)
                REFERENCES programmes(id),

            CONSTRAINT fk_conditions_admission_programme_pedagogique
                FOREIGN KEY (programme_pedagogique_id)
                REFERENCES programmes_pedagogiques(id),

            CONSTRAINT chk_conditions_admission_parent
                CHECK (
                    (programme_id IS NOT NULL AND programme_pedagogique_id IS NULL)
                    OR
                    (programme_id IS NULL AND programme_pedagogique_id IS NOT NULL)
                )
        )
    """)

    # 6. Tarifs
    op.execute("""
        CREATE TABLE tarifs (
            id SERIAL PRIMARY KEY,
            programme_id INTEGER,
            programme_pedagogique_id INTEGER,
            montant NUMERIC(12,2) NOT NULL,
            devise CHAR(3) NOT NULL DEFAULT 'TND',
            type_frais VARCHAR(50) NOT NULL,
            description TEXT,
            annee_academique VARCHAR(9) NOT NULL,
            actif BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_tarifs_programme
                FOREIGN KEY (programme_id)
                REFERENCES programmes(id),

            CONSTRAINT fk_tarifs_programme_pedagogique
                FOREIGN KEY (programme_pedagogique_id)
                REFERENCES programmes_pedagogiques(id),

            CONSTRAINT chk_tarifs_parent
                CHECK (
                    (programme_id IS NOT NULL AND programme_pedagogique_id IS NULL)
                    OR
                    (programme_id IS NULL AND programme_pedagogique_id IS NOT NULL)
                ),

            CONSTRAINT chk_tarifs_montant
                CHECK (montant >= 0),

            CONSTRAINT chk_tarifs_devise
                CHECK (devise IN ('TND', 'EUR', 'USD')),

            CONSTRAINT chk_tarifs_annee
                CHECK (annee_academique ~ '^[0-9]{4}-[0-9]{4}$')
        )
    """)

    # Index
    op.execute("""
        CREATE INDEX idx_specialites_programme
        ON specialites(programme_id)
    """)

    op.execute("""
        CREATE INDEX idx_programmes_pedagogiques_programme
        ON programmes_pedagogiques(programme_id)
    """)

    op.execute("""
        CREATE INDEX idx_programmes_pedagogiques_specialite
        ON programmes_pedagogiques(specialite_id)
    """)

    op.execute("""
        CREATE INDEX idx_matieres_programme_pedagogique
        ON matieres(programme_pedagogique_id)
    """)

    op.execute("""
        CREATE INDEX idx_pre_requis_matiere_requise
        ON pre_requis(matiere_requise_id)
    """)

    op.execute("""
        CREATE INDEX idx_conditions_admission_programme
        ON conditions_admission(programme_id)
    """)

    op.execute("""
        CREATE INDEX idx_conditions_admission_programme_pedagogique
        ON conditions_admission(programme_pedagogique_id)
    """)

    op.execute("""
        CREATE INDEX idx_tarifs_programme
        ON tarifs(programme_id)
    """)

    op.execute("""
        CREATE INDEX idx_tarifs_programme_pedagogique
        ON tarifs(programme_pedagogique_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tarifs")
    op.execute("DROP TABLE IF EXISTS conditions_admission")
    op.execute("DROP TABLE IF EXISTS pre_requis")
    op.execute("DROP TABLE IF EXISTS matieres")
    op.execute("DROP TABLE IF EXISTS programmes_pedagogiques")
    op.execute("DROP TABLE IF EXISTS specialites")