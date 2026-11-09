#!/usr/bin/env bash
# Ejecuta las fases 1 a 6 de la Entrega 1 y guarda la salida real de cada
# comando en evidencia/ (una carpeta ignorada por git).
# Uso:  cd mini-gestor-citas && bash scripts/ejecutar_entrega.sh
# Requiere: Docker Desktop abierto, python3, curl. Libres los puertos 5432 y 8000.
set -u
cd "$(dirname "$0")/.."
EV=evidencia
rm -rf "$EV"; mkdir -p "$EV"
[ -f .env ] || cp .env.example .env
set -a; . ./.env; set +a
CURRENT=""

fase() { CURRENT="$EV/$1.txt"; : > "$CURRENT"; printf '\n=== %s ===\n' "$2" | tee -a "$EV/00-resumen.txt"; }
# run '<comando>': muestra y guarda el comando tal cual (las variables $X
# quedan sin expandir en el registro, así no se escribe la contraseña).
run() {
  printf '$ %s\n' "$1" | tee -a "$CURRENT"
  eval "$1" 2>&1 | tee -a "$CURRENT"
  local rc=${PIPESTATUS[0]}
  [ "$rc" -ne 0 ] && printf '[código de salida: %s]\n' "$rc" | tee -a "$CURRENT"
  printf '\n' >> "$CURRENT"
  return 0
}
quiet() { eval "$1" >/dev/null 2>&1; }
esperar_db()  { for _ in $(seq 1 40); do docker exec citas-db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
esperar_api() { for _ in $(seq 1 40); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
prueba_api() {
  run 'curl -s -X POST http://localhost:8000/citas -H "Content-Type: application/json" -d @scripts/cita-ejemplo.json | python3 -m json.tool'
  run 'curl -s -X POST http://localhost:8000/citas -H "Content-Type: application/json" -d @scripts/cita-ejemplo-2.json | python3 -m json.tool'
  run 'curl -s http://localhost:8000/citas | python3 -m json.tool'
  run 'docker exec citas-db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM citas;"'
}
limpiar() {
  quiet 'docker compose down'
  quiet 'docker rm -f citas-api citas-db'
  quiet 'docker network rm citas-net'
  quiet 'docker volume rm citas-data'
}

# Puertos ocupados por algo que no sea Docker: se avisa y se detiene.
if ! docker info >/dev/null 2>&1; then echo "Docker no responde. Abre Docker Desktop y vuelve a ejecutar."; exit 1; fi
limpiar
for p in 5432 8000; do
  if lsof -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then echo "El puerto $p está ocupado por otro programa. Libéralo y vuelve a ejecutar."; exit 1; fi
done

fase 01-verificacion-docker "Fase 1 - Verificación del entorno Docker"
run 'docker --version'
run 'docker compose version'
run 'docker run --rm hello-world'

fase 02-postgres-contenedor "Fase 2 - PostgreSQL en un contenedor"
run 'docker run -d --name citas-db -e POSTGRES_USER=$POSTGRES_USER -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -e POSTGRES_DB=$POSTGRES_DB -v citas-data:/var/lib/postgresql/data -p 5432:5432 postgres:17'
esperar_db || echo "AVISO: PostgreSQL no respondió a tiempo" | tee -a "$CURRENT"
run 'docker ps --filter name=citas-db'
run 'docker volume ls --filter name=citas-data'

fase 03-api-sin-docker "Fase 3 - API sin Docker (localhost)"
run 'python3 -m venv .venv'
run '.venv/bin/pip install -q -r requirements.txt'
.venv/bin/uvicorn app.main:app --port 8000 > "$EV/03-uvicorn-local.log" 2>&1 &
UV_PID=$!
esperar_api || echo "AVISO: la API local no respondió a tiempo" | tee -a "$CURRENT"
run 'curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; print(*sorted(json.load(sys.stdin)[\"paths\"]), sep=chr(10))"'
run 'curl -s http://localhost:8000/health'
prueba_api
kill $UV_PID 2>/dev/null; wait $UV_PID 2>/dev/null
run 'docker exec citas-db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "DELETE FROM citas;"'

fase 04-dockerfile-imagen "Fase 4 - Imagen de la API con Dockerfile"
run 'cat Dockerfile'
run 'docker build -t citas-api .'
run 'docker images citas-api'

fase 05-comunicacion-manual "Fase 5 - Comunicación manual entre contenedores"
run 'docker network create citas-net'
run 'docker network connect citas-net citas-db'
run 'docker run -d --name citas-api --network citas-net -p 8000:8000 -e DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@citas-db:5432/$POSTGRES_DB citas-api'
esperar_api || echo "AVISO: la API en contenedor no respondió a tiempo" | tee -a "$CURRENT"
run 'docker ps'
run "docker network inspect citas-net --format '{{json .Containers}}' | python3 -m json.tool"
run 'docker logs citas-api'

fase 06-prueba-comunicacion "Prueba de comunicación entre contenedores"
prueba_api
run 'docker run --rm --network citas-net -e DB_MAX_RETRIES=2 -e DB_RETRY_SECONDS=1 -e DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB citas-api 2>&1 | tail -n 6'

fase 07-persistencia-volumen "Persistencia con volumen (docker run)"
run 'docker rm -f citas-db'
run 'docker run -d --name citas-db --network citas-net -e POSTGRES_USER=$POSTGRES_USER -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -e POSTGRES_DB=$POSTGRES_DB -v citas-data:/var/lib/postgresql/data -p 5432:5432 postgres:17'
esperar_db
run 'docker exec citas-db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM citas;"'
quiet 'docker rm -f citas-api citas-db'
quiet 'docker network rm citas-net'

fase 08-docker-compose "Fase 6 - Docker Compose"
run 'cat docker-compose.yml'
run 'docker compose up -d --build'
esperar_api || echo "AVISO: la API con Compose no respondió a tiempo" | tee -a "$CURRENT"
run 'docker compose ps'
run 'docker compose logs --tail 8 api'
prueba_api
run 'docker compose down'
run 'docker compose up -d'
esperar_api
run 'curl -s http://localhost:8000/citas | python3 -m json.tool'
run 'docker compose ps'

printf '\nListo. La salida de cada fase quedó en la carpeta evidencia/. Los contenedores siguen corriendo (docker compose down para detenerlos).\n' | tee -a "$EV/00-resumen.txt"
