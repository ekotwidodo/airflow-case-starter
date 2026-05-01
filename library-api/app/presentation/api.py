"""
api.py - FastAPI presentation layer for Library API
Defines all HTTP endpoints under /api/v1/:
  - POST/GET/PUT/DELETE /books: CRUD for db_library
  - GET /books/scraped: Read from db_scraping_raw
  - GET /books/integrator: Read from db_integrator (fact_books + dim_book)
  - GET /dashboard: Analytics from db_integrator (KPIs, distributions, recent books)
Rate limited to 10 req/min on POST /books via slowapi.
"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from oracledb import Connection
from contextlib import contextmanager

from app.domain.models import BookCreate, BookListResponse
from app.application.book_service import create_book, list_books
from app.infrastructure.database import get_connection, get_integrator_connection
from app.infrastructure.logging import log

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Library API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom error handler that returns structured JSON error responses."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": "ERROR", "message": exc.detail})


@contextmanager
def get_db():
    """Context manager for library database connection. Ensures connection is closed."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_integrator_db():
    """Context manager for integrator database connection. Ensures connection is closed."""
    conn = get_integrator_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.post("/api/v1/books", status_code=201)
@limiter.limit("10/minute")
def create_book_endpoint(book: BookCreate, request: Request):
    """Create a new book in db_library. Rate limited to 10/min."""
    try:
        with get_db() as db:
            result = create_book(db, book.model_dump())
            log.info("book_created", title=book.title, price=book.price)
            return result
    except Exception as e:
        log.error("book_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": str(e)})


@app.get("/api/v1/books")
def list_books_endpoint():
    """List all books from db_library."""
    try:
        with get_db() as db:
            books = list_books(db)
            log.info("books_listed", count=len(books))
            return books
    except Exception as e:
        log.error("books_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})


@app.get("/api/v1/dashboard")
def dashboard_endpoint():
    """Get dashboard analytics from db_integrator.
    Returns: total_books, total_categories, avg_price, rating_distribution,
             source_distribution, category_stats, recent_books.
    """
    try:
        with get_integrator_db() as db:
            cursor = db.cursor()

            # KPI: Total books in fact_books
            cursor.execute("SELECT COUNT(*) as total_books FROM fact_books")
            total_books = cursor.fetchone()[0]

            # KPI: Distinct categories
            cursor.execute(
                "SELECT COUNT(*) as total_categories FROM (SELECT DISTINCT category FROM fact_books WHERE category IS NOT NULL)"
            )
            total_categories = cursor.fetchone()[0]

            # KPI: Average price
            cursor.execute("SELECT AVG(price) as avg_price FROM fact_books")
            avg_price_row = cursor.fetchone()
            avg_price = float(avg_price_row[0]) if avg_price_row[0] else 0

            # Rating distribution: count per rating level
            cursor.execute(
                "SELECT rating, COUNT(*) as cnt FROM fact_books GROUP BY rating ORDER BY rating"
            )
            rating_dist = [{"rating": r[0], "count": r[1]} for r in cursor.fetchall()]

            # Source distribution: count per source (library vs scraper)
            cursor.execute(
                "SELECT source, COUNT(*) as cnt FROM fact_books GROUP BY source ORDER BY source"
            )
            source_dist = [{"source": r[0], "count": r[1]} for r in cursor.fetchall()]

            # Category stats: count and avg price per category (sorted by count desc)
            cursor.execute(
                "SELECT category, COUNT(*) as cnt, AVG(price) as avg_p FROM fact_books WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC"
            )
            category_stats = [{"category": r[0], "count": r[1], "avg_price": float(r[2]) if r[2] else 0} for r in cursor.fetchall()]

            # Recent books: latest 10 entries with title from dim_book
            cursor.execute(
                """SELECT b.title, f.price, f.rating, f.source, f.created_at
                   FROM fact_books f JOIN dim_book b ON f.book_sk = b.sk
                   ORDER BY f.created_at DESC FETCH FIRST 10 ROWS ONLY"""
            )
            columns = [col[0].lower() for col in cursor.description]
            recent_books = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for book in recent_books:
                if book.get("created_at"):
                    book["created_at"] = str(book["created_at"])

            cursor.close()
            log.info("dashboard_loaded")
            return {
                "total_books": total_books,
                "total_categories": total_categories,
                "avg_price": round(avg_price, 2),
                "rating_distribution": rating_dist,
                "source_distribution": source_dist,
                "category_stats": category_stats,
                "recent_books": recent_books
            }
    except Exception as e:
        log.error("dashboard_failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})


@app.get("/api/v1/books/scraped")
def list_scraped_books_endpoint():
    """List all scraped books from db_scraping_raw (RAW layer)."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, title, price, rating, availability, category, scraped_at FROM scraped_books_raw ORDER BY id")
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for row in results:
                if row.get("scraped_at"):
                    row["scraped_at"] = str(row["scraped_at"])
            cursor.close()
            log.info("scraped_books_listed", count=len(results))
            return results
    except Exception as e:
        log.error("scraped_books_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})


@app.get("/api/v1/books/integrator")
def list_integrator_books_endpoint():
    """List all books from db_integrator (MART layer) with source info."""
    try:
        with get_integrator_db() as db:
            cursor = db.cursor()
            cursor.execute(
                """SELECT b.sk, b.title, f.price, f.rating, f.category, f.source, f.created_at
                   FROM fact_books f JOIN dim_book b ON f.book_sk = b.sk
                   ORDER BY f.created_at DESC"""
            )
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            for row in results:
                if row.get("created_at"):
                    row["created_at"] = str(row["created_at"])
            cursor.close()
            log.info("integrator_books_listed", count=len(results))
            return results
    except Exception as e:
        log.error("integrator_books_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})


@app.put("/api/v1/books/{book_id}")
def update_book_endpoint(book_id: int, book: BookCreate, request: Request):
    """Update an existing book in db_library by ID."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE books SET title = :title, category = :category, price = :price, rating = :rating WHERE id = :id",
                {"title": book.title, "category": book.category, "price": book.price, "rating": book.rating, "id": book_id}
            )
            if cursor.rowcount == 0:
                cursor.close()
                raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Book not found"})
            db.commit()
            cursor.close()
            log.info("book_updated", id=book_id)
            return {"id": book_id, "status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        log.error("book_update_failed", error=str(e))
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": str(e)})


@app.delete("/api/v1/books/{book_id}")
def delete_book_endpoint(book_id: int):
    """Delete a book from db_library by ID. Propagates to integrator on next staging+mart run."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("DELETE FROM books WHERE id = :id", {"id": book_id})
            if cursor.rowcount == 0:
                cursor.close()
                raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Book not found"})
            db.commit()
            cursor.close()
            log.info("book_deleted", id=book_id)
            return {"id": book_id, "status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        log.error("book_delete_failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": str(e)})
