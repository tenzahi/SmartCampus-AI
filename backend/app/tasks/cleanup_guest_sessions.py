"""Scheduled cleanup entry point for expired visitor sessions."""

import argparse
import signal
import threading
import time

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.guest_session_service import cleanup_expired_guest_sessions

CLEANUP_ADVISORY_LOCK_ID = 230023


def run_cleanup_once(batch_size: int = 500) -> int | None:
    """Execute one cleanup pass protected by a PostgreSQL advisory lock."""
    with SessionLocal() as lock_db:
        is_postgres = lock_db.bind is not None and lock_db.bind.dialect.name == "postgresql"
        if is_postgres:
            acquired = bool(
                lock_db.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": CLEANUP_ADVISORY_LOCK_ID},
                ).scalar()
            )
            if not acquired:
                print("Nettoyage ignoré : une autre exécution est déjà en cours.")
                return None

        try:
            total_deleted = 0
            while True:
                with SessionLocal() as db:
                    deleted = cleanup_expired_guest_sessions(db, batch_size=batch_size)
                total_deleted += deleted
                if deleted < batch_size:
                    break
            print(f"Nettoyage terminé : {total_deleted} sessions expirées supprimées.")
            return total_deleted
        finally:
            if is_postgres:
                lock_db.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": CLEANUP_ADVISORY_LOCK_ID},
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supprime les sessions visiteurs expirées."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Intervalle en secondes pour une exécution périodique (0 = exécution unique).",
    )
    args = parser.parse_args()

    if args.interval <= 0:
        run_cleanup_once()
        return

    stop_event = threading.Event()

    def _handle_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    while not stop_event.is_set():
        try:
            run_cleanup_once()
        except Exception as exc:
            print(f"Erreur lors du nettoyage périodique : {exc}")
        if stop_event.wait(timeout=args.interval):
            break


if __name__ == "__main__":
    main()
