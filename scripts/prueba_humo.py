"""Prueba de humo del contenedor de la API.

Comprueba que la imagen real de la API (la misma que construye el pipeline y que
arranca con uvicorn) responde por la red: espera a que /health conteste y luego
crea y consulta una cita. Solo usa la biblioteca estándar de Python, así que se
puede ejecutar desde cualquier contenedor que tenga Python:

    python prueba_humo.py http://citas-ci-api-N:8000

Termina con código 1 si la API no responde a tiempo o si alguna respuesta no es
la esperada.
"""
import json
import sys
import time
import urllib.error
import urllib.request

ESPERA_MAXIMA = 60  # segundos: al arrancar, la API se conecta a PostgreSQL y crea la tabla
CITA = {"nombre": "Prueba de humo", "fecha_hora": "2026-12-01T09:00:00", "motivo": "Verificar"}


def pedir(base, metodo, ruta, datos=None):
    """Hace una petición HTTP y devuelve (código de estado, cuerpo)."""
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    peticion = urllib.request.Request(
        base + ruta, data=cuerpo, method=metodo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=5) as respuesta:
            return respuesta.status, json.loads(respuesta.read())
    except urllib.error.HTTPError as exc:  # 4xx o 5xx: se devuelve para revisarlo
        return exc.code, exc.read().decode(errors="replace")


def fallar(mensaje):
    print(f"[humo] ERROR: {mensaje}", flush=True)
    sys.exit(1)


def esperar_api(base):
    """Reintenta /health hasta que responda 200 o se agote la espera."""
    limite = time.monotonic() + ESPERA_MAXIMA
    while True:
        try:
            estado, cuerpo = pedir(base, "GET", "/health")
            if estado == 200:
                return cuerpo
            motivo = f"/health devolvió {estado}"
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            motivo = str(exc)  # el contenedor todavía no acepta conexiones
        if time.monotonic() >= limite:
            fallar(f"la API no respondió en {ESPERA_MAXIMA} s ({motivo})")
        time.sleep(2)


def main(base):
    salud = esperar_api(base)
    if salud != {"estado": "ok"}:
        fallar(f"/health respondió {salud}")
    print(f"[humo] /health responde: {salud}", flush=True)

    estado, creada = pedir(base, "POST", "/citas", CITA)
    if estado != 201 or not isinstance(creada, dict) or creada.get("nombre") != CITA["nombre"]:
        fallar(f"POST /citas devolvió {estado}: {creada}")

    estado, consultada = pedir(base, "GET", f"/citas/{creada['id']}")
    if estado != 200 or consultada != creada:
        fallar(f"GET /citas/{creada['id']} devolvió {estado}: {consultada}")
    print(f"[humo] cita {creada['id']} creada y consultada: el contenedor de la API funciona",
          flush=True)


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000")
