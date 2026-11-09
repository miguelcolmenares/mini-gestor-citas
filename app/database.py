"""Conexión a PostgreSQL y modelo de la tabla citas."""
import os
from datetime import datetime

from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# La URL llega por variable de entorno. Fuera de Docker se usa localhost;
# dentro de la red de Docker se usa el nombre del contenedor (citas-db).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://citas_user:cambiar_esta_clave@localhost:5432/citas",
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


class Cita(Base):
    __tablename__ = "citas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    motivo: Mapped[str] = mapped_column(String(200))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
