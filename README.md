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
├── tests/                # pruebas de la API (pytest)
├── jenkins/              # imagen de Jenkins con Docker CLI y plugins
├── docs/                 # documento de implementación de Jenkins
├── requirements.txt      # dependencias de Python
├── requirements-test.txt # dependencias de pruebas y lint
├── ruff.toml             # reglas del lint
├── Jenkinsfile           # pipeline de integración continua
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
4. **Calidad de código (lint)**: construye la imagen de pruebas y revisa el código con [ruff](https://docs.astral.sh/ruff/) (errores, estilo PEP 8 y orden de imports, según `ruff.toml`). Si encuentra problemas, el pipeline se detiene.
5. **Levantar base de datos de prueba**: un PostgreSQL temporal en una red de Docker propia de esa ejecución.
6. **Pruebas**: corre `pytest` (carpeta `tests/`) contra esa base de datos, conectándose por el nombre del contenedor. Mide la **cobertura** con `pytest-cov` y falla si baja del 80 %. Jenkins guarda el reporte de las pruebas (JUnit) y el de cobertura (`reportes/cobertura.xml`, en los artefactos de la ejecución).

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

## Calidad de código y cobertura (Entrega 2)

- `tests/test_api.py`: flujo principal de la API (crear, consultar, listar, 404).
- `tests/test_validaciones.py`: datos inválidos (campos vacíos, faltantes o demasiado largos, fecha inválida, id no numérico), orden del listado, `/health` con la base de datos caída y los reintentos de conexión al arrancar.
- `ruff.toml`: reglas del lint que corre el pipeline.

En total son 18 pruebas y cubren el 100 % del código de `app/`.

El documento con las características requeridas para la implementación de Jenkins está en `docs/`.

### Correr las pruebas sin Jenkins

Con la base de datos de la Entrega 1 corriendo (`docker compose up -d db`):

```bash
pip install -r requirements-test.txt
ruff check .
python -m pytest -v --cov=app --cov-report=term-missing
```

Las pruebas usan la `DATABASE_URL` de `localhost`. Si en el `.env` se cambió la clave, exportar antes `DATABASE_URL` con esos valores.


## Entrega 2 (Semana 5): Jenkins como gestor de operaciones

**Objetivo:** documentar las características requeridas para implementar Jenkins y fortalecer el pipeline para que no solo compruebe que el código compila y que las pruebas pasan, sino que también controle su **calidad**.

### Qué se hizo

- **Documento de implementación** (`docs/Implementacion_Jenkins_Mini_Gestor_Citas.docx`): requerimientos de hardware y software, plugins, red y puertos, almacenamiento, seguridad, arquitectura, instalación, diseño del pipeline, disparadores, mantenimiento y evidencias.
- **Nueva etapa "Calidad de código (lint)"**: revisa el código con [ruff](https://docs.astral.sh/ruff/) según `ruff.toml` (errores, estilo PEP 8 y orden de imports).
- **Cobertura de pruebas** con `pytest-cov`: el pipeline falla si la cobertura baja del 80 % y guarda `reportes/cobertura.xml` como artefacto de cada ejecución.
- **13 pruebas nuevas** en `tests/test_validaciones.py`: campos vacíos, faltantes o demasiado largos, fecha inválida, id no numérico, orden del listado, `/health` con la base de datos caída y reintentos de conexión al arrancar.

### Pipeline actualizado

| # | Etapa | Qué hace | Falla si... |
|---|---|---|---|
| 1 | Verificar herramientas | Muestra las versiones de Docker y Docker Compose y el último commit. | Falta alguna herramienta. |
| 2 | Construir imagen de la API | `docker build` con el `Dockerfile`. | La imagen no se construye. |
| 3 | Validar docker-compose.yml | `docker compose config --quiet`. | El archivo de Compose no es válido. |
| 4 | **Calidad de código (lint)** *(nueva)* | Construye la imagen de pruebas y ejecuta `ruff check .`. | Hay errores o problemas de estilo. |
| 5 | Levantar base de datos de prueba | PostgreSQL 17 temporal en una red propia de la ejecución. | La base de datos no arranca en 60 s. |
| 6 | Pruebas *(con cobertura)* | `pytest` contra la base de datos, con reportes JUnit y de cobertura. | Falla alguna prueba o la cobertura baja del 80 %. |

### Compuertas de calidad

Una compuerta de calidad es una regla que detiene el pipeline cuando el código no cumple un mínimo. Con estas dos, un cambio con errores o sin pruebas no puede quedar en verde:

1. **Lint sin errores** (etapa 4).
2. **Cobertura mínima del 80 %** (etapa 6).

### Resultados de la ejecución

Pipeline ejecutado en **Jenkins 2.580.2** (LTS, Java 21) sobre Docker Desktop:

- Las **6 etapas en verde**, en aproximadamente 1 min 16 s.
- **18 pruebas exitosas**, 0 fallidas y 0 omitidas (5 de `test_api` y 13 de `test_validaciones`).
- **Cobertura del 100 %** del código de `app/`.

Las capturas de estas ejecuciones están en la sección de evidencias del documento de `docs/`.

### Correr el lint y las pruebas sin Jenkins

Con la base de datos de la Entrega 1 corriendo (`docker compose up -d db`):

```bash
pip install -r requirements-test.txt
ruff check .
python -m pytest -v --cov=app --cov-report=term-missing --cov-fail-under=80
```

Las pruebas usan la `DATABASE_URL` de `localhost`. Si en el `.env` se cambió la clave, exportar antes `DATABASE_URL` con esos valores.

