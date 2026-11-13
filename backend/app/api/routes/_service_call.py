from typing import Callable, TypeVar

from app.core.exceptions import SmartCampusException


T = TypeVar("T")


def call_service(call: Callable[[], T], error_message: str) -> T:
    """Exécuter un appel de service en conservant les erreurs métier.

    Les erreurs non prévues sont converties en 500 sans exposer les détails
    internes au client, comme pour le CRUD Formations existant.
    """
    try:
        return call()
    except SmartCampusException:
        raise
    except Exception:
        raise SmartCampusException(message=error_message, status_code=500)
