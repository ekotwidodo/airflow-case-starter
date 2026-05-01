"""
etl_tasks.py - Shared ETL functions for Airflow DAGs
Contains all task callables used by scraping_dag, staging_dag, and mart_dag.
Each function is designed to be called by PythonOperator via python_callable.
Data is passed between tasks via XCom (JSON serialized).

Pipeline layers:
  RAW (db_scraping_raw) -> STG (db_staging) -> MART (db_integrator)
  db_library is also merged into STG during staging_dag.

Full synchronization: staging and mart DAGs use TRUNCATE + RELOAD
to ensure deletes/edits in source databases propagate downstream.
"""
import oracledb
import json
import hashlib
from datetime import datetime


def get_connection(dsn: str, user: str, password: str) -> oracledb.Connection:
    """Create Oracle database connection.

    Args:
        dsn: Connection string (host:port/service)
        user: Database username
        password: Database password

    Returns:
        Active oracledb.Connection
    """
    return oracledb.connect(user=user, password=password, dsn=dsn)


# ==================== SCRAPING DAG TASKS ====================

def fetch_html_fn(**context):
    """Task: Fetch HTML from books.toscrape.com catalog page 1.
    Pushes HTML content to XCom for the next task.
    """
    import requests
    resp = requests.get("http://books.toscrape.com/catalogue/page-1.html", timeout=10)
    resp.raise_for_status()
    context['ti'].xcom_push(key='html', value=resp.text)
    return "fetched"


def parse_books_fn(**context):
    """Task: Parse book data from HTML, extract categories from detail pages.
    For each book, navigates to its detail page to get category from breadcrumb.
    Pushes parsed books (list of dicts) to XCom.
    """
    import requests
    from bs4 import BeautifulSoup
    html = context['ti'].xcom_pull(key='html', task_ids='fetch_html')
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select(".product_pod")[:10]
    books = []
    for p in products:
        title = p.h3.a["title"]
        href = p.h3.a["href"]
        price_str = p.select_one(".price_color").text
        price = float("".join(c for c in price_str if c.isdigit() or c == "."))
        rating_class = p.select_one(".star-rating")["class"][1]
        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

        # Extract category from detail page breadcrumb
        category = None
        try:
            if href.startswith("../"):
                detail_url = "http://books.toscrape.com/" + href.replace("../", "")
            else:
                detail_url = "http://books.toscrape.com/catalogue/" + href
            resp = requests.get(detail_url, timeout=10)
            if resp.status_code == 200:
                detail_soup = BeautifulSoup(resp.text, "html.parser")
                breadcrumb = detail_soup.select_one("ul.breadcrumb")
                if breadcrumb:
                    links = breadcrumb.select("a")
                    if len(links) >= 2:
                        category = links[-1].text.strip()
        except Exception:
            pass

        books.append({
            "title": title,
            "price": price,
            "rating": rating_map.get(rating_class, 0),
            "availability": p.select_one(".instock.availability").text.strip() if p.select_one(".instock.availability") else "Unknown",
            "category": category,
            "sk": hashlib.sha256(f"{title}{price}".encode()).hexdigest()
        })
    context['ti'].xcom_push(key='books', value=json.dumps(books))
    return f"parsed {len(books)} books"


def validate_schema_fn(**context):
    """Task: Validate parsed books (price > 0, rating >= 1).
    Filters out invalid records and pushes validated books to XCom.
    """
    books_raw = json.loads(context['ti'].xcom_pull(key='books', task_ids='parse_books'))
    validated = []
    for b in books_raw:
        if b.get("price", 0) > 0 and b.get("rating", 0) >= 1:
            validated.append(b)
    context['ti'].xcom_push(key='validated_books', value=json.dumps(validated))
    return f"validated {len(validated)} books"


def load_raw_fn(**context):
    """Task: Load validated books into db_scraping_raw (RAW layer).
    Append-only: skips books that already exist (by title+price match).
    Failed inserts go to dlq_books table.
    """
    import os
    books = json.loads(context['ti'].xcom_pull(key='validated_books', task_ids='validate_schema'))
    conn = get_connection(
        dsn=f"{os.getenv('SCRAPING_RAW_HOST', 'oracle')}:{os.getenv('SCRAPING_RAW_PORT', '1521')}/{os.getenv('SCRAPING_RAW_SERVICE', 'BOOKSDB')}",
        user=os.getenv("SCRAPING_RAW_USER", "system"),
        password=os.getenv("SCRAPING_RAW_PASSWORD", "oracle123")
    )
    cursor = conn.cursor()
    count = 0
    for book in books:
        try:
            cursor.execute("SELECT 1 FROM scraped_books_raw WHERE title = :t AND price = :p",
                         {"t": book["title"], "p": book["price"]})
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO scraped_books_raw (title, price, rating, availability, category) VALUES (:t, :p, :r, :a, :c)",
                    {"t": book["title"], "p": book["price"], "r": book["rating"], "a": book["availability"], "c": book.get("category")}
                )
                count += 1
        except Exception as e:
            cursor.execute(
                "INSERT INTO dlq_books (payload, error_message, created_at) VALUES (:p, :e, SYSDATE)",
                {"p": json.dumps(book), "e": str(e)[:500]}
            )
    conn.commit()
    cursor.close()
    conn.close()
    return f"loaded {count} new books"


# ==================== STAGING DAG TASKS ====================

def extract_raw_fn(**context):
    """Task: Extract books from BOTH db_scraping_raw AND db_library.
    Merges both sources with a 'source' tag ('scraper' or 'library').
    Pushes combined list to XCom for staging processing.
    """
    import os
    # Extract from scraping raw database
    raw_conn = get_connection(
        dsn=f"{os.getenv('SCRAPING_RAW_HOST', 'oracle')}:{os.getenv('SCRAPING_RAW_PORT', '1521')}/{os.getenv('SCRAPING_RAW_SERVICE', 'BOOKSDB')}",
        user=os.getenv("SCRAPING_RAW_USER", "system"),
        password=os.getenv("SCRAPING_RAW_PASSWORD", "oracle123")
    )
    cursor = raw_conn.cursor()
    cursor.execute("SELECT title, price, rating, availability, category, scraped_at FROM scraped_books_raw")
    rows = cursor.fetchall()
    books = [{"title": r[0], "price": float(r[1]), "rating": int(r[2]), "availability": r[3], "category": r[4], "scraped_at": str(r[5]), "source": "scraper"} for r in rows]
    cursor.close()
    raw_conn.close()

    # Extract from library database
    lib_conn = get_connection(
        dsn=f"{os.getenv('DB_LIBRARY_HOST', 'oracle')}:{os.getenv('DB_LIBRARY_PORT', '1521')}/{os.getenv('DB_LIBRARY_SERVICE', 'BOOKSDB')}",
        user=os.getenv("DB_LIBRARY_USER", "system"),
        password=os.getenv("DB_LIBRARY_PASSWORD", "oracle123")
    )
    cursor = lib_conn.cursor()
    cursor.execute("SELECT title, category, price, rating, created_at FROM books")
    rows = cursor.fetchall()
    lib_books = [{"title": r[0], "price": float(r[2]), "rating": int(r[3]), "category": r[1], "scraped_at": str(r[4]), "source": "library"} for r in rows]
    cursor.close()
    lib_conn.close()

    all_books = books + lib_books
    context['ti'].xcom_push(key='raw_books', value=json.dumps(all_books))
    return f"extracted {len(books)} scraped + {len(lib_books)} library = {len(all_books)} total"


def validate_data_fn(**context):
    """Task: Validate merged books for staging (price > 0, rating 1-5).
    Stricter than raw validation: rating must be <= 5.
    """
    books = json.loads(context['ti'].xcom_pull(key='raw_books', task_ids='extract_raw'))
    validated = []
    for b in books:
        if b.get("price", 0) > 0 and 1 <= b.get("rating", 0) <= 5:
            validated.append(b)
    context['ti'].xcom_push(key='validated_stg', value=json.dumps(validated))
    return f"validated {len(validated)} for staging"


def deduplicate_fn(**context):
    """Task: Deduplicate merged books by SK = SHA-256(title + price).
    If the same book exists in both scraper and library sources, only one survives.
    Adds processed_at timestamp for tracking.
    """
    books = json.loads(context['ti'].xcom_pull(key='validated_stg', task_ids='validate_data'))
    seen = set()
    deduped = []
    for b in books:
        sk = hashlib.sha256(f"{b['title']}{b['price']}".encode()).hexdigest()
        if sk not in seen:
            seen.add(sk)
            b["sk"] = sk
            b["category"] = b.get("category")
            b["processed_at"] = datetime.now().isoformat()
            deduped.append(b)
    context['ti'].xcom_push(key='deduped_books', value=json.dumps(deduped))
    return f"deduplicated to {len(deduped)} books"


def load_staging_fn(**context):
    """Task: Full sync load into db_staging (STG layer).
    TRUNCATE + RELOAD ensures deleted records in source DBs are removed.
    This is the key synchronization point for the pipeline.
    """
    import os
    books = json.loads(context['ti'].xcom_pull(key='deduped_books', task_ids='deduplicate'))
    conn = get_connection(
        dsn=f"{os.getenv('STAGING_HOST', 'oracle')}:{os.getenv('STAGING_PORT', '1521')}/{os.getenv('STAGING_SERVICE', 'BOOKSDB')}",
        user=os.getenv("STAGING_USER", "system"),
        password=os.getenv("STAGING_PASSWORD", "oracle123")
    )
    cursor = conn.cursor()
    # Full sync: truncate and reload all records
    cursor.execute("TRUNCATE TABLE stg_books")
    for book in books:
        cursor.execute(
            """INSERT INTO stg_books (sk, title, category, price, rating, source, processed_at)
               VALUES (:sk, :title, :category, :price, :rating, :source, SYSDATE)""",
            {"sk": book["sk"], "title": book["title"], "category": book.get("category"), "price": book["price"], "rating": book["rating"], "source": book["source"]}
        )
    conn.commit()
    cursor.close()
    conn.close()
    return f"reloaded {len(books)} books to staging (full sync)"


# ==================== MART DAG TASKS ====================

def extract_staging_fn(**context):
    """Task: Extract all books from db_staging for mart processing."""
    import os
    conn = get_connection(
        dsn=f"{os.getenv('STAGING_HOST', 'oracle')}:{os.getenv('STAGING_PORT', '1521')}/{os.getenv('STAGING_SERVICE', 'BOOKSDB')}",
        user=os.getenv("STAGING_USER", "system"),
        password=os.getenv("STAGING_PASSWORD", "oracle123")
    )
    cursor = conn.cursor()
    cursor.execute("SELECT sk, title, category, price, rating, source FROM stg_books")
    rows = cursor.fetchall()
    books = [{"sk": r[0], "title": r[1], "category": r[2], "price": float(r[3]), "rating": int(r[4]), "source": r[5]} for r in rows]
    cursor.close()
    conn.close()
    context['ti'].xcom_push(key='stg_books', value=json.dumps(books))
    return f"extracted {len(books)} from staging"


def upsert_dim_book_fn(**context):
    """Task: Sync dim_book table in db_integrator (MART layer).
    Full sync: deletes orphan records (SKs not in staging), then MERGE for new/updated.
    Ensures dim_book always reflects the current staging state.
    """
    import os
    books = json.loads(context['ti'].xcom_pull(key='stg_books', task_ids='extract_staging'))
    conn = get_connection(
        dsn=f"{os.getenv('INTEGRATOR_HOST', 'oracle')}:{os.getenv('INTEGRATOR_PORT', '1521')}/{os.getenv('INTEGRATOR_SERVICE', 'BOOKSDB')}",
        user=os.getenv("INTEGRATOR_USER", "system"),
        password=os.getenv("INTEGRATOR_PASSWORD", "oracle123")
    )
    cursor = conn.cursor()

    # Delete orphans: records in dim_book but not in current staging
    staging_sks = [b["sk"] for b in books]
    if staging_sks:
        placeholders = ", ".join([f":sk{i}" for i in range(len(staging_sks))])
        bind_vars = {f"sk{i}": sk for i, sk in enumerate(staging_sks)}
        cursor.execute(f"DELETE FROM dim_book WHERE sk NOT IN ({placeholders})", bind_vars)
    else:
        cursor.execute("DELETE FROM dim_book")

    # Insert or update records from staging
    for book in books:
        cursor.execute(
            """MERGE INTO dim_book d
               USING (SELECT :sk AS sk, :title AS title FROM dual) s
               ON (d.sk = s.sk)
               WHEN NOT MATCHED THEN INSERT (sk, title) VALUES (s.sk, s.title)""",
            {"sk": book["sk"], "title": book["title"]}
        )
    conn.commit()
    cursor.close()
    conn.close()
    return f"synced {len(books)} dim_book records (full sync)"


def insert_fact_fn(**context):
    """Task: Full sync load into fact_books in db_integrator (MART layer).
    TRUNCATE + RELOAD ensures fact_books always matches staging state.
    Dashboard queries read from this table.
    """
    import os
    books = json.loads(context['ti'].xcom_pull(key='stg_books', task_ids='extract_staging'))
    conn = get_connection(
        dsn=f"{os.getenv('INTEGRATOR_HOST', 'oracle')}:{os.getenv('INTEGRATOR_PORT', '1521')}/{os.getenv('INTEGRATOR_SERVICE', 'BOOKSDB')}",
        user=os.getenv("INTEGRATOR_USER", "system"),
        password=os.getenv("INTEGRATOR_PASSWORD", "oracle123")
    )
    cursor = conn.cursor()
    # Full sync: truncate and reload all records
    cursor.execute("TRUNCATE TABLE fact_books")
    for book in books:
        cursor.execute(
            """INSERT INTO fact_books (book_sk, category, price, rating, source, created_at)
               VALUES (:sk, :category, :price, :rating, :source, SYSDATE)""",
            {"sk": book["sk"], "category": book.get("category"), "price": book["price"], "rating": book["rating"], "source": book["source"]}
        )
    conn.commit()
    cursor.close()
    conn.close()
    return f"reloaded {len(books)} fact records (full sync)"
