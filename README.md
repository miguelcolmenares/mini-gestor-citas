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
