# script para crear todas las tablas desde Python

"""
Correr una sola vez para crear el schema:
    python -m db.init_db
"""
from db.connection import engine, Base, test_connection
import db.models  # noqa: F401 — importar para que Base registre los modelos


def init():
    test_connection()
    print("🔨 Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Schema creado correctamente")
    print("\nTablas creadas:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    init()