"""
loader.py - Database loader functions for scraper service
Provides:
  - get_db_connection(): Oracle connection to db_scraping_raw
  - load_raw(): Insert book into scraped_books_raw (skip if duplicate)
  - load_dlq(): Insert failed record into dlq_books for error tracking
"""
import oracledb
import json
from typing import Optional


def get_db_connection() -> oracledb.Connection:
    """Create connection to db_scraping_raw using environment variables."""
    import os
    host = os.getenv("SCRAPING_RAW_HOST", "localhost")
    port = os.getenv("SCRAPING_RAW_PORT", "1521")
    service = os.getenv("SCRAPING_RAW_SERVICE", "BOOKSDB")
    user = os.getenv("SCRAPING_RAW_USER", "raw_user")
    password = os.getenv("SCRAPING_RAW_PASSWORD", "raw_pass")
    dsn = f"{host}:{port}/{service}"
    return oracledb.connect(user=user, password=password, dsn=dsn)


def load_raw(book: dict, conn: oracledb.Connection) -> bool:
    """Insert a book into scraped_books_raw if it doesn't already exist.
    Deduplication is based on title+price match (not SK).
    Failed inserts are sent to DLQ.

    Args:
        book: Dict with title, price, rating, availability, category
        conn: Active Oracle connection

    Returns:
        True if inserted, False if duplicate
    """
    cursor = conn.cursor()
    try:
        # Check for existing book with same title and price
        cursor.execute(
            "SELECT 1 FROM scraped_books_raw WHERE title = :title AND price = :price",
            {"title": book["title"], "price": book["price"]}
        )
        if cursor.fetchone():
            return False
        cursor.execute(
            "INSERT INTO scraped_books_raw (title, price, rating, availability, category) VALUES (:title, :price, :rating, :availability, :category)",
            {"title": book["title"], "price": book["price"], "rating": book["rating"], "availability": book["availability"], "category": book.get("category")}
        )
        conn.commit()
        return True
    except Exception as e:
        load_dlq(book, str(e))
        return False
    finally:
        cursor.close()


def load_dlq(payload: Optional[dict], error_message: str):
    """Insert a failed record into dlq_books for later inspection.
    Silently fails if DLQ insert itself fails (avoid infinite loops).

    Args:
        payload: The book data that failed (or None)
        error_message: Error description (truncated to 500 chars)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO dlq_books (payload, error_message, created_at) VALUES (:payload, :error_message, SYSDATE)",
            {"payload": json.dumps(payload) if payload else None, "error_message": error_message[:500]}
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass
