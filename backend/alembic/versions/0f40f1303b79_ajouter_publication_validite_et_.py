"""ajouter publication validite et paiement aux informations admission

Revision ID: 0f40f1303b79
Revises: 086731756304
Create Date: 2026-11-24 20:20:42.052693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f40f1303b79"
down_revision: Union[str, None] = "086731756304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================
    # TABLE TARIFS
    # =========================

    op.add_column(
        "tarifs",
        sa.Column(
            "modalite_paiement",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "tarifs",
        sa.Column(
            "statut_publication",
            sa.String(length=20),
            nullable=False,
            server_default="publie",
        ),
    )

    op.add_column(
        "tarifs",
        sa.Column(
            "date_debut_validite",
            sa.Date(),
            nullable=True,
        ),
    )

    op.add_column(
        "tarifs",
        sa.Column(
            "date_fin_validite",
            sa.Date(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "chk_tarifs_statut_publication",
        "tarifs",
        "statut_publication IN ('brouillon', 'publie', 'archive')",
    )

    op.create_check_constraint(
        "chk_tarifs_validite",
        "tarifs",
        "date_fin_validite IS NULL "
        "OR date_debut_validite IS NULL "
        "OR date_fin_validite >= date_debut_validite",
    )

    # =========================
    # TABLE CONDITIONS_ADMISSION
    # =========================

    op.add_column(
        "conditions_admission",
        sa.Column(
            "statut_publication",
            sa.String(length=20),
            nullable=False,
            server_default="publie",
        ),
    )

    op.add_column(
        "conditions_admission",
        sa.Column(
            "date_debut_validite",
            sa.Date(),
            nullable=True,
        ),
    )

    op.add_column(
        "conditions_admission",
        sa.Column(
            "date_fin_validite",
            sa.Date(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "chk_conditions_statut_publication",
        "conditions_admission",
        "statut_publication IN ('brouillon', 'publie', 'archive')",
    )

    op.create_check_constraint(
        "chk_conditions_validite",
        "conditions_admission",
        "date_fin_validite IS NULL "
        "OR date_debut_validite IS NULL "
        "OR date_fin_validite >= date_debut_validite",
    )


def downgrade() -> None:
    # =========================
    # TABLE CONDITIONS_ADMISSION
    # =========================

    op.drop_constraint(
        "chk_conditions_validite",
        "conditions_admission",
        type_="check",
    )

    op.drop_constraint(
        "chk_conditions_statut_publication",
        "conditions_admission",
        type_="check",
    )

    op.drop_column(
        "conditions_admission",
        "date_fin_validite",
    )

    op.drop_column(
        "conditions_admission",
        "date_debut_validite",
    )

    op.drop_column(
        "conditions_admission",
        "statut_publication",
    )

    # =========================
    # TABLE TARIFS
    # =========================

    op.drop_constraint(
        "chk_tarifs_validite",
        "tarifs",
        type_="check",
    )

    op.drop_constraint(
        "chk_tarifs_statut_publication",
        "tarifs",
        type_="check",
    )

    op.drop_column(
        "tarifs",
        "date_fin_validite",
    )

    op.drop_column(
        "tarifs",
        "date_debut_validite",
    )

    op.drop_column(
        "tarifs",
        "statut_publication",
    )

    op.drop_column(
        "tarifs",
        "modalite_paiement",
    )