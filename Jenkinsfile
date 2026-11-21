// Pipeline de integración continua del Mini Gestor de Citas (Entrega 2).
// Cada ejecución construye la imagen de la API, levanta una base de datos
// PostgreSQL temporal, corre las pruebas contra ella y al final borra todo.
pipeline {
    agent any

    // Jenkins corre en un computador local, así que GitHub no le puede avisar
    // con un webhook. En su lugar Jenkins revisa el repositorio cada 5 minutos.
    triggers {
        pollSCM('H/5 * * * *')
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
    }

    environment {
        // Nombres únicos por ejecución para no chocar con los contenedores
        // de desarrollo (citas-api, citas-db) ni con otra ejecución.
        IMAGEN_API  = "citas-api:ci-${env.BUILD_NUMBER}"
        IMAGEN_TEST = "citas-api-tests:ci-${env.BUILD_NUMBER}"
        RED         = "citas-ci-net-${env.BUILD_NUMBER}"
        DB          = "citas-ci-db-${env.BUILD_NUMBER}"
        PRUEBAS     = "citas-ci-pruebas-${env.BUILD_NUMBER}"
        // Credenciales solo para la base de datos temporal de las pruebas.
        POSTGRES_USER     = 'citas_ci'
        POSTGRES_PASSWORD = 'citas_ci'
        POSTGRES_DB       = 'citas'
    }

    stages {
        stage('Verificar herramientas') {
            steps {
                sh 'docker --version'
                sh 'docker compose version'
                sh 'git log -1 --oneline'
            }
        }

        stage('Construir imagen de la API') {
            steps {
                sh 'docker build -t "$IMAGEN_API" .'
            }
        }

        stage('Validar docker-compose.yml') {
            steps {
                // Revisa que el archivo de Compose de la Entrega 1 siga siendo válido.
                sh 'cp .env.example .env && docker compose config --quiet && echo "docker-compose.yml válido"'
            }
        }

        stage('Levantar base de datos de prueba') {
            steps {
                // Por si una ejecución anterior se cortó y dejó restos.
                sh 'docker rm -f "$PRUEBAS" "$DB" >/dev/null 2>&1 || true; docker network rm "$RED" >/dev/null 2>&1 || true'
                sh 'docker network create "$RED"'
                sh '''
                    docker run -d --name "$DB" --network "$RED" \
                      -e POSTGRES_USER="$POSTGRES_USER" \
                      -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
                      -e POSTGRES_DB="$POSTGRES_DB" \
                      postgres:17
                '''
                // Espera hasta 60 segundos a que PostgreSQL acepte conexiones.
                sh '''
                    for i in $(seq 1 30); do
                      docker exec "$DB" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" && exit 0
                      sleep 2
                    done
                    echo "PostgreSQL no arrancó a tiempo"; exit 1
                '''
            }
        }

        stage('Pruebas') {
            steps {
                sh 'docker build -f Dockerfile.test --build-arg IMAGEN_API="$IMAGEN_API" -t "$IMAGEN_TEST" .'
                // La API de las pruebas se conecta a la BD por el nombre del
                // contenedor, igual que en la Entrega 1.
                sh '''
                    docker run --name "$PRUEBAS" --network "$RED" \
                      -e DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$DB:5432/$POSTGRES_DB" \
                      "$IMAGEN_TEST"
                '''
            }
            post {
                always {
                    // Copia el reporte de pytest para que Jenkins muestre los resultados.
                    sh 'mkdir -p reportes && docker cp "$PRUEBAS":/code/reportes/pruebas.xml reportes/ || true'
                    junit allowEmptyResults: true, testResults: 'reportes/pruebas.xml'
                }
            }
        }
    }

    post {
        always {
            // Limpieza: se borra todo lo que se creó en esta ejecución.
            sh '''
                docker rm -f "$PRUEBAS" "$DB" || true
                docker network rm "$RED" || true
                docker rmi "$IMAGEN_TEST" "$IMAGEN_API" || true
                rm -f .env
            '''
        }
        success {
            echo 'Integración exitosa: la imagen se construyó y todas las pruebas pasaron.'
        }
        failure {
            echo 'La integración falló. Revisar la etapa en rojo y los resultados de las pruebas.'
        }
    }
}
