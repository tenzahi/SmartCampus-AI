from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.models import User
from app.db.session import SessionLocal


DEMO_USERS = [
    {
        "email": "admin@smartcampus.tn",
        "password": "Admin123!",
        "full_name": "Administrateur SmartCampus",
        "role": "admin",
    },
    {
        "email": "resp.iit@smartcampus.tn",
        "password": "RespIIT123!",
        "full_name": "Responsable IIT",
        "role": "resp_iit",
    },
    {
        "email": "resp.isb@smartcampus.tn",
        "password": "RespISB123!",
        "full_name": "Responsable ISB",
        "role": "resp_isb",
    },
]


def main():
    db = SessionLocal()

    try:
        for data in DEMO_USERS:
            existing = db.scalar(
                select(User).where(User.email == data["email"])
            )

            if existing:
                print(
                    f"Utilisateur déjà existant : "
                    f"{data['email']} (id={existing.id}, role={existing.role})"
                )
                continue

            user = User(
                email=data["email"],
                password_hash=get_password_hash(data["password"]),
                full_name=data["full_name"],
                role=data["role"],
                is_active=True,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            print(
                f"Utilisateur créé : "
                f"{user.email} (id={user.id}, role={user.role})"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()