from sqlalchemy.orm import Session
from db.models import User, UserRole
from db.connection import get_db
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_user_by_email(email: str) -> User | None:
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Forzar carga de todos los atributos antes de cerrar la sesión
            db.expunge(user)
            from sqlalchemy.orm import make_transient
            make_transient(user)
        return user


def login(email: str, password: str) -> User | None:
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password):
            return None
        # Cargar atributos y desacoplar de la sesión
        db.expunge(user)
        from sqlalchemy.orm import make_transient
        make_transient(user)
        return user


def register(name: str, email: str, password: str) -> User:
    if get_user_by_email(email):
        raise ValueError("Ya existe una cuenta con ese email.")
    with get_db() as db:
        user = User(
            name=name,
            email=email,
            password=hash_password(password),
            role=UserRole.customer,
        )
        db.add(user)
        db.flush()
        db.expunge(user)
        from sqlalchemy.orm import make_transient
        make_transient(user)
        return user


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin