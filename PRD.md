# PRD — Product Requirements Document (Books Ecosystem Data Platform)

## 1. Overview

Platform data engineering end-to-end untuk ekosistem data buku yang mencakup:
- Manajemen buku manual melalui UI (CRUD)
- Scraping data buku dari website eksternal
- Pipeline ETL yang menggabungkan kedua sumber data
- Dashboard analitik untuk insight bisnis

## 2. Goals

### Business Goals
- Menyediakan single source of truth untuk data buku dari berbagai sumber
- Memungkinkan analisis kategori, rating, dan harga buku
- Mendukung pengambilan keputusan berbasis data

### Technical Goals
- Production-grade data pipeline dengan monitoring dan alerting
- Idempotent dan resilient terhadap failure
- Clean Architecture untuk maintainability
- Separation of concerns: RAW → STAGING → MART

## 3. Users

| Role | Description |
|------|-------------|
| End User | Mengelola buku melalui UI (create, edit, delete) |
| Data Engineer | Mengelola dan monitoring ETL pipeline |
| Business Analyst | Mengakses dashboard untuk insight |
| Backend Engineer | Mengembangkan dan memaintain API |
| DevOps | Mengelola infrastruktur dan deployment |

## 4. Features

### 4.1 Library Management (OLTP)
- **Create Book**: User input buku baru melalui modal form (symmetrical dengan edit form)
- **List Books**: Tampilkan daftar buku dengan filter, kolom `#` (nomor urut, bukan ID database)
- **Edit Book**: Update data buku melalui modal form
- **Delete Book**: Hapus buku dari database (dengan konfirmasi)
- **Validation**: Client-side dan server-side (title required, price > 0, rating 1-5)

### 4.2 Web Scraping (Ingestion)
- **Auto-scrape**: Fetch data buku dari books.toscrape.com
- **Category Extraction**: Extract kategori dari breadcrumb halaman detail buku
- **Deduplication**: Hash(title + price) untuk menghindari duplikasi
- **Error Handling**: Retry 3x, DLQ untuk data yang gagal

### 4.3 ETL Pipeline (Processing)
Platform menggunakan model **full synchronization** — semua database downstream di-refresh dari sumber upstream pada setiap DAG run, sehingga delete dan edit di sumber ter-propagasi ke dashboard.

- **Scraping DAG** (setiap 20 menit):
  - Fetch HTML → Parse books → Validate schema → Append ke RAW (append-only, scraper sebagai source of truth)
- **Staging DAG** (setiap 40 menit):
  - Extract dari scraping DB + library DB → Merge → Validate → Deduplicate → **TRUNCATE + RELOAD** ke STG (full sync — delete di sumber ter-propagasi)
- **Mart DAG** (setiap 1 jam):
  - Extract dari STG → **Sync dim_book** (add new, remove orphans) → **TRUNCATE + RELOAD fact_books** (full sync — dashboard selalu mencerminkan state staging)

### 4.4 Sinkronisasi Database

| Aksi | Efek pada Downstream |
|------|---------------------|
| Delete buku di `db_library` | Dihapus dari `db_staging` pada staging run berikutnya → dihapus dari `db_integrator` pada mart run berikutnya → dashboard mencerminkan penghapusan |
| Delete buku di `db_scraping_raw` | Dihapus dari `db_staging` pada staging run berikutnya → dihapus dari `db_integrator` pada mart run berikutnya |
| Edit buku di `db_library` | Diupdate di `db_staging` pada staging run berikutnya → diupdate di `db_integrator` pada mart run berikutnya |
| Add buku di salah satu sumber | Ditambahkan ke `db_staging` pada staging run berikutnya → ditambahkan ke `db_integrator` pada mart run berikutnya |

### 4.5 Logika Deduplikasi

Buku dari kedua sumber dideduplikasi berdasarkan `SK = SHA-256(title + price)`. Jika buku yang sama ada di `db_library` dan `db_scraping_raw`, hanya 1 record yang bertahan di `db_staging` dan `db_integrator`:
- Library: 10 buku, Scraping: 10 buku → Integrator: ≤ 20 buku (tergantung overlap)
- Delete 1 buku dari Library → Integrator: ≤ 19 buku setelah staging + mart run berikutnya

### 4.6 Dashboard (Serving)
- **KPI Cards**: Total books, total categories, average price
- **Rating Distribution**: Bar chart distribusi rating (1-5 stars)
- **Source Distribution**: Bar chart distribusi sumber data (Library vs Scraping)
- **Category Stats**: Top categories dengan bar chart dan count (tanpa harga)
- **Recent Books**: 10 buku terbaru yang masuk ke data mart (title, price, rating, source)

## 5. Data Model

### 5.1 Database Schema
| Database | Layer | Tables | Purpose |
|----------|-------|--------|---------|
| db_library | OLTP | books | Manual book management |
| db_scraping_raw | RAW | scraped_books_raw, dlq_books | Raw scraped data |
| db_staging | STG | stg_books | Cleaned & merged data |
| db_integrator | MART | dim_book, fact_books, etl_watermark | Dimensional model |

### 5.2 Data Lineage
| Target | Source | Transformation |
|--------|--------|---------------|
| stg_books.sk | hash(title + price) | SHA-256 |
| stg_books.title | scraped_books_raw.title / books.title | Direct |
| stg_books.category | books.toscrape.com breadcrumb | Parsed |
| fact_books.book_sk | stg_books.sk | Direct |
| fact_books.price | stg_books.price | Cleaned |
| fact_books.rating | stg_books.rating | Validated (1-5) |
| fact_books.source | stg_books.source | Direct (library / scraper) |

## 6. Non-Functional Requirements

### Performance
- API latency < 2 detik
- Dashboard load < 3 detik
- Scraping DAG SLA: 30 menit
- Staging DAG SLA: 45 menit
- Mart DAG SLA: 60 menit

### Reliability
- Pipeline retry: 3x dengan delay 5 menit
- Idempotent pipeline (dapat di-rerun tanpa duplikasi)
- DLQ untuk data yang gagal diproses

### Security
- DB credentials via environment variables
- Rate limiting pada API (10 req/min)
- Role-based access (Airflow admin)

### Scalability
- Index pada sk dan created_at
- Partitioning pada fact_books by created_at
- Horizontal scaling untuk Airflow workers

## 7. Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Database | Oracle Database 21c XE |
| Scraper | Python, requests, BeautifulSoup |
| Orchestration | Apache Airflow 2.7 |
| Frontend | React, TypeScript, Axios |
| Web Server (Frontend) | Nginx |
| Containerization | Docker, Docker Compose |
| Logging | JSON structured logging |

## 8. Success Metrics

- **Data Freshness**: Data scraping tersedia dalam 30 menit dari perubahan website
- **Data Quality**: 0 duplikasi, validasi rating dan price 100%
- **Pipeline Reliability**: > 99% successful DAG runs
- **API Availability**: > 99.9% uptime
- **User Experience**: Dashboard load < 3 detik

## 9. Out of Scope

- User authentication untuk frontend (phase 2)
- Real-time streaming data (phase 2)
- Multi-tenant support (phase 2)
- Advanced analytics / ML predictions (phase 3)

## 10. Future Enhancements

- Pagination dan search/filter pada Book Scrap dan Book All
- Export data ke CSV/Excel
- Alerting otomatis ke Slack/Email saat DAG gagal
- Data lineage tracking dengan OpenMetadata / Amundsen
- Schema registry untuk evolusi schema
