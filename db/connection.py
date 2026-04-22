from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager
from config.settings import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # verifica conexión antes de usarla
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_db():
    """Context manager para usar en services. Cierra la sesión automáticamente."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def test_connection():
    """Útil para verificar que la DB está levantada."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión a PostgreSQL OK")