"""Pruebas de la API. Se ejecutan contra una base de datos PostgreSQL real
(en Jenkins es un contenedor temporal que se crea solo para las pruebas)."""
from fastapi.testclient import TestClient

from app.main import app

CITA = {"nombre": "Prueba Jenkins", "fecha_hora": "2026-12-01T10:00:00", "motivo": "Control"}


def cliente():
    # Usar el cliente con "with" ejecuta el arranque de la API (crea la tabla).
    return TestClient(app)


def test_health_responde_ok():
    with cliente() as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_crear_cita_la_guarda_en_la_base_de_datos():
    with cliente() as c:
        creada = c.post("/citas", json=CITA)
        assert creada.status_code == 201
        cita = creada.json()
        assert cita["id"] > 0
        assert cita["nombre"] == CITA["nombre"]

        consultada = c.get(f"/citas/{cita['id']}")
    assert consultada.status_code == 200
    assert consultada.json() == cita


def test_listar_citas_incluye_la_cita_creada():
    with cliente() as c:
        nueva = c.post("/citas", json={**CITA, "nombre": "Otra persona"}).json()
        r = c.get("/citas")
    assert r.status_code == 200
    assert nueva["id"] in [cita["id"] for cita in r.json()]


def test_cita_que_no_existe_devuelve_404():
    with cliente() as c:
        r = c.get("/citas/999999")
    assert r.status_code == 404


def test_no_deja_crear_cita_sin_nombre():
    with cliente() as c:
        r = c.post("/citas", json={**CITA, "nombre": ""})
    assert r.status_code == 422
