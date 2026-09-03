# HT4 - Herramientas

Agente de preguntas frecuentes de Parachute S.A. con recuperación semántica
sobre PostgreSQL y pgvector.

## Arquitectura

El proyecto utiliza los siguientes componentes:

- PostgreSQL 17 con pgvector 0.8.6.
- Vectores de 384 dimensiones generados con `all-MiniLM-L6-v2`.
- Índice HNSW con distancia coseno.
- Cliente de PostgreSQL mediante Psycopg.
- Un agente compatible con el SDK de OpenAI.

La tabla `faq_embeddings` almacena el identificador, categoría, pregunta,
respuesta, metadatos, huella del contenido y embedding de cada FAQ.
El módulo `config.py` centraliza las variables que utilizarán el cargador y el
agente.

## Requisitos

- Docker con Docker Compose.
- Python 3.10 o superior.

## Configuración

Copie el archivo de variables de entorno:

```bash
cp .env.example .env
```

Los valores incluidos permiten ejecutar PostgreSQL localmente. Antes de usar el
agente se debe completar `LLM_API_KEY` en `.env`. El archivo `.env` está excluido
del repositorio.

Si el puerto 5432 ya está ocupado, cambie `POSTGRES_PORT` y actualice el puerto
de `DATABASE_URL` con el mismo valor.

## Inicialización de PostgreSQL

Inicie la base de datos:

```bash
docker compose up -d
```

Docker creará el volumen persistente, habilitará la extensión `vector` y
ejecutará `db/init.sql` para preparar la tabla y sus índices.

Compruebe que el servicio esté saludable:

```bash
docker compose ps
```

Verifique la extensión y la tabla:

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT extname, extversion FROM pg_extension WHERE extname = '\''vector'\'';"'
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\d+ faq_embeddings"'
```

Para detener la infraestructura sin eliminar los datos:

```bash
docker compose down
```

Para crear nuevamente la base desde cero:

```bash
docker compose down --volumes
docker compose up -d
```

El primer comando elimina permanentemente el volumen local y sus registros.

## Entorno de Python

Prepare el entorno virtual e instale las dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para ejecutar las pruebas durante el desarrollo:

```bash
pip install -r requirements-dev.txt
pytest
```

## Esquema compartido

| Columna | Tipo | Uso |
| --- | --- | --- |
| `id` | `BIGSERIAL` | Clave interna |
| `faq_id` | `VARCHAR(20)` | Identificador único del corpus |
| `category` | `TEXT` | Categoría de la FAQ |
| `question` | `TEXT` | Pregunta original |
| `answer` | `TEXT` | Respuesta respaldada por el corpus |
| `metadata` | `JSONB` | Datos adicionales del registro |
| `content_hash` | `CHAR(64)` | Control de cambios e idempotencia |
| `embedding` | `VECTOR(384)` | Representación semántica |
| `created_at` | `TIMESTAMPTZ` | Fecha de creación |
| `updated_at` | `TIMESTAMPTZ` | Fecha de última actualización |

Las búsquedas semánticas deben ordenar por distancia coseno con el operador
`<=>` y limitar la cantidad de resultados solicitados por el agente.
