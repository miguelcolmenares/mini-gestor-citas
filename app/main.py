"""API del Mini Gestor de Citas (FastAPI + PostgreSQL)."""
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .database import Base, Cita, engine, get_db

DB_MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", "15"))
DB_RETRY_SECONDS = float(os.getenv("DB_RETRY_SECONDS", "2"))


def preparar_base_de_datos() -> None:
    """Crea la tabla; reintenta mientras PostgreSQL termina de arrancar."""
    for intento in range(1, DB_MAX_RETRIES + 1):
        try:
            Base.metadata.create_all(bind=engine)
            print("[db] conexión establecida y tabla citas lista", flush=True)
            return
        except OperationalError as exc:
            print(f"[db] intento {intento}/{DB_MAX_RETRIES} fallido: {exc.orig}", flush=True)
            if intento == DB_MAX_RETRIES:
                raise
            time.sleep(DB_RETRY_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    preparar_base_de_datos()
    yield


app = FastAPI(title="Mini Gestor de Citas", version="1.0.0", lifespan=lifespan)


class CitaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    fecha_hora: datetime
    motivo: str = Field(min_length=1, max_length=200)


class CitaOut(CitaIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"estado": "ok"}


@app.post("/citas", response_model=CitaOut, status_code=201)
def crear_cita(datos: CitaIn, db: Session = Depends(get_db)):
    cita = Cita(**datos.model_dump())
    db.add(cita)
    db.commit()
    db.refresh(cita)
    return cita


@app.get("/citas", response_model=list[CitaOut])
def listar_citas(db: Session = Depends(get_db)):
    return db.scalars(select(Cita).order_by(Cita.id)).all()


@app.get("/citas/{cita_id}", response_model=CitaOut)
def obtener_cita(cita_id: int, db: Session = Depends(get_db)):
    cita = db.get(Cita, cita_id)
    if cita is None:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita
