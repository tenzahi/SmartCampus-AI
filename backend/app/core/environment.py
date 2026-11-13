"""Détection de l'environnement d'exécution.

Variables reconnues, par ordre de priorité : ``APP_ENV``, ``ENVIRONMENT``,
``ENV``. Les valeurs ``production`` et ``prod`` (insensibles à la casse)
activent le mode production. Toute autre valeur, ou l'absence de variable,
correspond au mode développement.

Ce module ne lit aucun secret et ne journalise rien.
"""

import os

ENVIRONMENT_VARIABLES = ("APP_ENV", "ENVIRONMENT", "ENV")
PRODUCTION_VALUES = frozenset({"production", "prod"})
DEFAULT_ENVIRONMENT = "development"


def get_environment() -> str:
    """Retourne l'environnement courant en minuscules."""
    for variable in ENVIRONMENT_VARIABLES:
        value = os.getenv(variable)
        if value and value.strip():
            return value.strip().lower()
    return DEFAULT_ENVIRONMENT


def is_production() -> bool:
    """Indique si l'application s'exécute en production."""
    return get_environment() in PRODUCTION_VALUES
