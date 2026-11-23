"""Pruebas de validación de datos y de manejo de errores de la API.
Complementan test_api.py: revisan que la API rechace datos inválidos y que
responda bien cuando la base de datos falla."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import main
from app.database import get_db
from app.main import app

CITA = {"nombre": "Prueba Validaciones", "fecha_hora": "2026-12-01T10:00:00", "motivo": "Control"}


def cliente():
    return TestClient(app)


@pytest.mark.parametrize(
    "cambios",
    [
        {"motivo": ""},                    # motivo vacío
        {"nombre": "x" * 101},             # nombre de más de 100 caracteres
        {"motivo": "x" * 201},             # motivo de más de 200 caracteres
        {"fecha_hora": "no-es-una-fecha"},  # fecha con formato inválido
    ],
)
def test_rechaza_cita_con_datos_invalidos(cambios):
    with cliente() as c:
        r = c.post("/citas", json={**CITA, **cambios})
    assert r.status_code == 422


@pytest.mark.parametrize("campo", ["nombre", "fecha_hora", "motivo"])
def test_rechaza_cita_sin_campo_obligatorio(campo):
    datos = {k: v for k, v in CITA.items() if k != campo}
    with cliente() as c:
        r = c.post("/citas", json=datos)
    assert r.status_code == 422


def test_acepta_nombre_y_motivo_en_el_limite_de_longitud():
    with cliente() as c:
        r = c.post("/citas", json={**CITA, "nombre": "n" * 100, "motivo": "m" * 200})
    assert r.status_code == 201


def test_id_no_numerico_devuelve_422():
    with cliente() as c:
        r = c.get("/citas/abc")
    assert r.status_code == 422


def test_listar_citas_las_devuelve_ordenadas_por_id():
    with cliente() as c:
        c.post("/citas", json=CITA)
        c.post("/citas", json=CITA)
        ids = [cita["id"] for cita in c.get("/citas").json()]
    assert ids == sorted(ids)


def test_health_devuelve_503_si_la_base_de_datos_no_responde():
    class SesionCaida:
        def execute(self, *_):
            raise OperationalError("SELECT 1", {}, Exception("sin conexión"))

    app.dependency_overrides[get_db] = lambda: SesionCaida()
    try:
        with cliente() as c:
            r = c.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json()["detail"] == "Base de datos no disponible"


def test_arranque_reintenta_mientras_la_base_de_datos_no_esta_lista(monkeypatch):
    intentos = {"n": 0}

    def create_all_falla_dos_veces(**_):
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise OperationalError("CREATE TABLE", {}, Exception("aún arrancando"))

    monkeypatch.setattr(main.Base.metadata, "create_all", create_all_falla_dos_veces)
    monkeypatch.setattr(main, "DB_RETRY_SECONDS", 0)
    main.preparar_base_de_datos()
    assert intentos["n"] == 3


def test_arranque_falla_si_se_agotan_los_reintentos(monkeypatch):
    def create_all_siempre_falla(**_):
        raise OperationalError("CREATE TABLE", {}, Exception("caída"))

    monkeypatch.setattr(main.Base.metadata, "create_all", create_all_siempre_falla)
    monkeypatch.setattr(main, "DB_RETRY_SECONDS", 0)
    monkeypatch.setattr(main, "DB_MAX_RETRIES", 2)
    with pytest.raises(OperationalError):
        main.preparar_base_de_datos()
