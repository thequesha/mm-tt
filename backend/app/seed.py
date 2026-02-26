from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_admin(db: Session) -> None:
    existing = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
    if existing:
        return
    admin = User(
        username=settings.ADMIN_USERNAME,
        password_hash=pwd_context.hash(settings.ADMIN_PASSWORD),
    )
    db.add(admin)
    db.commit()
    print(f"[seed] Admin user '{settings.ADMIN_USERNAME}' created.")
