# DE Airflow Oracles - Books Ecosystem Data Platform

Production-grade data engineering platform for books data ecosystem built with modern data stack.

## Architecture

```
Library API (FastAPI) --> db_library
                               \
                                --> STAGING (db_staging) --> MART (db_integrator) --> Dashboard API
                               /
Scraper Service (Python) ----> RAW (db_scraping_raw)
```

### Data Flow

The platform uses a **full synchronization** model. All downstream databases are refreshed from their upstream sources on each DAG run, ensuring deletes and edits propagate through the pipeline.

```
db_library (OLTP) ──┐
                     ├──> STAGING DAG (full sync) ──> db_staging ──> MART DAG (full sync) ──> db_integrator ──> Dashboard
db_scraping_raw ────┘
```

1. **Scraping DAG** (every 20 min): Fetches books from books.toscrape.com, extracts categories from detail pages, validates, deduplicates by hash(title+price), **appends** to `db_scraping_raw` (append-only, scraper is the source of truth)
2. **Frontend + Library API**: Users manually add/edit/delete books via UI → stored in `db_library` (OLTP, full CRUD)
3. **Staging DAG** (every 40 min): Extracts from BOTH `db_scraping_raw` AND `db_library`, merges, validates, deduplicates by SK, **TRUNCATE + RELOAD** `db_staging` (full sync — deletes in source DBs propagate here)
4. **Mart DAG** (every 1 hour): Extracts from `db_staging`, **syncs `dim_book`** (adds new, removes orphans), **TRUNCATE + RELOAD `fact_books`** (full sync — dashboard always reflects staging state)
5. **Library API**: Dual DB connection — CRUD on `db_library`, Dashboard queries from `db_integrator`

### Synchronization Behavior

| Action | Effect on Downstream |
|--------|---------------------|
| Delete book in `db_library` | Removed from `db_staging` on next staging run → removed from `db_integrator` on next mart run → dashboard reflects deletion |
| Delete book in `db_scraping_raw` | Removed from `db_staging` on next staging run → removed from `db_integrator` on next mart run |
| Edit book in `db_library` | Updated in `db_staging` on next staging run → updated in `db_integrator` on next mart run |
| Add book in either source | Added to `db_staging` on next staging run → added to `db_integrator` on next mart run |

### Deduplication Logic

Books from both sources are deduplicated by `SK = SHA-256(title + price)`. If the same book exists in both `db_library` and `db_scraping_raw`, only one record survives in `db_staging` and `db_integrator`. This means:
- Library: 10 books, Scraping: 10 books → Integrator: ≤ 20 books (depends on overlap)
- Delete 1 book from Library → Integrator: ≤ 19 books after next staging + mart run

## Services

| Service | Description | Tech Stack |
|---------|-------------|------------|
| Library API | CRUD + Dashboard API with dual DB connections | FastAPI, Oracle DB |
| Scraper Service | Web scraping with category extraction from detail pages | Python, BeautifulSoup, Requests |
| Airflow | Orchestrates ETL pipelines (scraping → staging → mart) | Apache Airflow 2.7 |
| Frontend | Books management UI with 4 views | React, Axios |
| Oracle DB | Single Oracle XE instance hosting all 4 databases | Oracle 21c XE |

## Frontend Views

| View | Description | Data Source |
|------|-------------|-------------|
| Book List | CRUD books with add/edit/delete modals, `#` column (order number), filter, pagination | db_library |
| Book Scrap | Shows scraped books with categories | db_scraping_raw |
| Book All | Shows merged books from integrator | db_integrator (fact_books + dim_book) |
| Dashboard | KPIs, rating distribution, source distribution, category stats (count only), recent books | db_integrator |

## Databases

All databases run on a single Oracle XE instance, separated by schema:

| Database | Layer | Tables | Purpose |
|----------|-------|--------|---------|
| db_library | OLTP | books | Manual book management via Library API |
| db_scraping_raw | RAW | scraped_books_raw, dlq_books | Raw scraped data (append-only) |
| db_staging | STG | stg_books | Cleaned, validated, deduplicated data (full sync) |
| db_integrator | MART | dim_book, fact_books | Dimensional model for dashboard (full sync) |

## Quick Start

### Prerequisites

- **Docker** (v20+) and **Docker Compose** (v2.0+)
- **PowerShell** (Windows) or **bash** (Linux/macOS)
- Minimum 8GB RAM (Oracle XE requires ~4GB)

### Step 1: Clone and Navigate

```bash
cd de-airflow-oracles
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts 7 services:
- `oracle` — Oracle Database 21c XE (port 1521)
- `library-api` — FastAPI backend (port 8000)
- `scraper` — One-shot scraper service (runs once and exits)
- `frontend` — React UI via Nginx (port 3000)
- `airflow-postgres` — PostgreSQL for Airflow metadata
- `airflow-webserver` — Airflow UI (port 8080)
- `airflow-scheduler` — Airflow DAG scheduler

Wait ~2 minutes for Oracle to fully initialize. Check status:
```bash
docker ps
```

### Step 3: Run Database Migrations

Execute SQL migrations to create tables in each database schema:

```powershell
# db_library: Create books table
Get-Content "migrations/db_library/V1__init.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB

# db_scraping_raw: Create scraped_books_raw and dlq_books tables
Get-Content "migrations/db_scraping_raw/V1__init_scraped_books_raw.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB

# db_staging: Create stg_books table
Get-Content "migrations/db_staging/V1__init_stg_books.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB

# db_integrator: Create dim_book, fact_books, etl_watermark tables
Get-Content "migrations/db_integrator/V1__init_mart.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB

# db_integrator: Add watermark table
Get-Content "migrations/db_integrator/V2__add_watermark.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB

# db_scraping_raw: Add DLQ table
Get-Content "migrations/db_integrator/V3__add_dlq.sql" | docker exec -i de-airflow-oracles-oracle-1 sqlplus -L system/oracle123@//localhost:1521/BOOKSDB
```

### Step 4: Initialize Airflow

```bash
# Initialize Airflow metadata database
docker-compose up airflow-init

# Create admin user
docker exec de-airflow-oracles-airflow-webserver-1 airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com
```

### Step 5: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | None |
| Library API Docs | http://localhost:8000/docs | None |
| Airflow UI | http://localhost:8080 | admin / admin |
| Oracle DB | localhost:1521 | system / oracle123 |

### Step 6: Run the Pipeline

1. **Unpause DAGs** in Airflow UI (http://localhost:8080)
2. **Trigger scraping_dag** manually to populate RAW data
3. **Trigger staging_dag** to merge RAW + Library → STG
4. **Trigger mart_dag** to populate dim_book + fact_books
5. **Visit Dashboard** at http://localhost:3000 to see analytics

Or trigger via CLI:
```bash
docker exec de-airflow-oracles-airflow-webserver-1 airflow dags trigger scraping_dag
docker exec de-airflow-oracles-airflow-webserver-1 airflow dags trigger staging_dag
docker exec de-airflow-oracles-airflow-webserver-1 airflow dags trigger mart_dag
```

### Step 7: Add Books via UI

1. Go to http://localhost:3000
2. Click **"+ Add Book"** to open the create modal
3. Fill in title, category, price, rating
4. Click **"Create"**
5. Books appear in the list with edit/delete actions

## Project Structure

```
├── migrations/                    # SQL database migrations (Flyway-style)
│   ├── db_library/               # OLTP schema: books table
│   ├── db_scraping_raw/          # RAW schema: scraped_books_raw, dlq_books
│   ├── db_staging/               # STG schema: stg_books
│   └── db_integrator/            # MART schema: dim_book, fact_books
├── library-api/                   # FastAPI application (Clean Architecture)
│   ├── app/
│   │   ├── domain/               # Pydantic models (validation)
│   │   ├── application/          # Business logic (pure functions)
│   │   ├── presentation/         # API endpoints (FastAPI routes)
│   │   └── infrastructure/       # DB connections, logging
│   └── tests/
├── scraper-service/               # Python scraper service
│   ├── src/
│   │   ├── scraper.py            # Main scraper: fetch, parse, load
│   │   ├── config.py             # Configuration constants
│   │   ├── loader.py             # DB loader functions
│   │   └── logging_config.py     # Structured logging setup
│   └── tests/
├── airflow/                       # Airflow orchestration
│   ├── dags/                     # DAG definitions
│   │   ├── scraping_dag.py       # RAW layer pipeline
│   │   ├── staging_dag.py        # STG layer pipeline
│   │   └── mart_dag.py           # MART layer pipeline
│   └── plugins/
│       └── etl_tasks.py          # Shared ETL task functions
├── frontend/                      # React frontend
│   ├── src/
│   │   ├── App.tsx               # Main app with navigation
│   │   ├── api/
│   │   │   └── books.ts          # API client (axios wrappers)
│   │   └── components/
│   │       ├── BookList.tsx      # CRUD view with modals
│   │       ├── BookScrap.tsx     # Scraped books view
│   │       ├── BookAll.tsx       # Integrator books view
│   │       └── Dashboard.tsx     # Analytics dashboard
│   └── package.json
├── docker/                        # Docker configuration
│   ├── Dockerfile.oracle         # Oracle XE base image
│   ├── Dockerfile.library-api    # FastAPI + oracledb
│   ├── Dockerfile.scraper-service# Python scraper
│   ├── Dockerfile.frontend       # Multi-stage: Node build → Nginx
│   ├── Dockerfile.airflow        # Airflow + oracledb + bs4
│   └── nginx.conf                # Nginx proxy config for frontend
├── docker-compose.yml             # Main compose file (7 services)
├── .env.dev                       # Development environment variables
├── README.md                      # This file
└── PRD.md                         # Product Requirements Document
```

## ETL Pipelines

| DAG | Description | Schedule | Cron | SLA |
|-----|-------------|----------|------|-----|
| scraping_dag | Scrape books + categories → append to RAW | Every 20 min | `*/20 * * * *` | 30 min |
| staging_dag | Merge scraping + library → clean → TRUNCATE+RELOAD STG | Every 40 min | `*/40 * * * *` | 45 min |
| mart_dag | Sync dim_book + TRUNCATE+RELOAD fact_books | Every 1 hour | `0 * * * *` | 60 min |

## API Endpoints

| Method | Endpoint | Description | DB |
|--------|----------|-------------|----|
| POST | /api/v1/books | Create book (rate limited: 10/min) | db_library |
| GET | /api/v1/books | List books | db_library |
| PUT | /api/v1/books/{id} | Update book | db_library |
| DELETE | /api/v1/books/{id} | Delete book | db_library |
| GET | /api/v1/books/scraped | List scraped books | db_scraping_raw |
| GET | /api/v1/books/integrator | List integrator books | db_integrator |
| GET | /api/v1/dashboard | Dashboard analytics | db_integrator |

## Environment Variables

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| DB_LIBRARY_HOST | library-api | Library DB hostname | oracle |
| DB_LIBRARY_PORT | library-api | Library DB port | 1521 |
| DB_LIBRARY_USER | library-api | Library DB username | system |
| DB_LIBRARY_PASSWORD | library-api | Library DB password | oracle123 |
| SCRAPING_RAW_HOST | scraper, airflow | Scraping DB hostname | oracle |
| SCRAPING_RAW_USER | scraper, airflow | Scraping DB username | system |
| SCRAPING_RAW_PASSWORD | scraper, airflow | Scraping DB password | oracle123 |
| STAGING_HOST | airflow | Staging DB hostname | oracle |
| STAGING_USER | airflow | Staging DB username | system |
| STAGING_PASSWORD | airflow | Staging DB password | oracle123 |
| INTEGRATOR_HOST | library-api, airflow | Integrator DB hostname | oracle |
| INTEGRATOR_USER | library-api, airflow | Integrator DB username | system |
| INTEGRATOR_PASSWORD | library-api, airflow | Integrator DB password | oracle123 |

## Troubleshooting

### Oracle not ready
Wait 1-2 minutes after `docker-compose up`. Check logs:
```bash
docker logs de-airflow-oracles-oracle-1 -f
```

### Airflow DAGs not appearing
Ensure migrations ran successfully and Airflow services are healthy:
```bash
docker exec de-airflow-oracles-airflow-webserver-1 airflow dags list
```

### Frontend shows no data
1. Run scraping_dag to populate RAW data
2. Add books via UI to populate library data
3. Run staging_dag and mart_dag to propagate to integrator

### Reset everything
```bash
docker-compose down -v
docker-compose up -d
# Then re-run migrations and Airflow init
```

## Production Readiness

See `tdd_production.md` for full technical design and production readiness checklist.
