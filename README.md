# Mini Gestor de Citas

Proyecto del módulo Énfasis Profesional I (Integración Continua) - Politécnico Grancolombiano, Subgrupo B03 Grupo 07.

API REST en Python (FastAPI) para crear y consultar citas, con base de datos PostgreSQL. Ambos servicios corren en contenedores Docker y se comunican por una red de Docker.

## Estructura

```
mini-gestor-citas/
├── app/
│   ├── main.py           # endpoints de la API (FastAPI)
│   └── database.py       # conexión a PostgreSQL y modelo Cita
├── scripts/              # ejemplos de citas y script que ejecuta todas las fases
├── requirements.txt      # dependencias de Python
├── Dockerfile            # imagen propia de la API
├── docker-compose.yml    # API + PostgreSQL con un solo comando
├── .env.example          # variables de entorno de ejemplo
└── README.md
```

## Cómo levantar el proyecto

1. Copiar `.env.example` a `.env` y ajustar los valores.
2. `docker compose up -d --build`
3. Abrir http://localhost:8000/docs

Endpoints: `POST /citas`, `GET /citas`, `GET /citas/{id}`, `GET /health`.

Para repetir todas las fases de la Entrega 1 y guardar la salida en `evidencia/`: `bash scripts/ejecutar_entrega.sh`.

## Integración continua con Jenkins (Entrega 2)

Jenkins corre en su propio contenedor y usa el Docker del computador para construir la imagen de la API y correr las pruebas. El pipeline está en el `Jenkinsfile` y tiene estas etapas:

1. **Verificar herramientas**: versiones de Docker, Docker Compose y el último commit.
2. **Construir imagen de la API**: `docker build` con el `Dockerfile` de la Entrega 1.
3. **Validar docker-compose.yml**: revisa que el archivo de Compose siga siendo válido.
4. **Levantar base de datos de prueba**: un PostgreSQL temporal en una red de Docker propia de esa ejecución.
5. **Pruebas**: corre `pytest` (carpeta `tests/`) contra esa base de datos, conectándose por el nombre del contenedor. Jenkins guarda el reporte de las pruebas.

Al final se borran los contenedores, la red y las imágenes de esa ejecución, pase o falle. Los nombres llevan el número de ejecución, así que no chocan con los contenedores de desarrollo (`citas-api`, `citas-db`).

### Levantar Jenkins

Requiere Docker Desktop abierto y el puerto 8080 libre.

```bash
cd jenkins
docker compose up -d --build
docker exec citas-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Abrir http://localhost:8080, pegar la contraseña, instalar los plugins sugeridos y crear el usuario administrador. Los plugins que necesita el pipeline ya vienen instalados (`jenkins/plugins.txt`).

### Crear el pipeline

1. **Nueva Tarea** → nombre `mini-gestor-citas` → tipo **Pipeline**.
2. En **Pipeline**, elegir **Pipeline script from SCM** → **Git**.
3. URL del repositorio: `https://github.com/miguelcolmenares/mini-gestor-citas.git` (es público, no necesita credenciales).
4. Rama: `*/main`. Script Path: `Jenkinsfile`.
5. Guardar y dar clic en **Construir ahora**.

Como Jenkins corre en un computador local, GitHub no le puede avisar con un webhook. Por eso el `Jenkinsfile` tiene `pollSCM('H/5 * * * *')`: Jenkins revisa el repositorio cada 5 minutos y, si hay commits nuevos, ejecuta el pipeline solo.

### Correr las pruebas sin Jenkins

Con la base de datos de la Entrega 1 corriendo (`docker compose up -d db`):

```bash
pip install -r requirements-test.txt
python -m pytest -v
```

Las pruebas usan la `DATABASE_URL` de `localhost`. Si en el `.env` se cambió la clave, exportar antes `DATABASE_URL` con esos valores.
