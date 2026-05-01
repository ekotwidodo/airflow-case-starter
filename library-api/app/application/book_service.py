"""
book_service.py - Business logic layer for book operations
Contains pure functions that operate on database connections.
Follows Clean Architecture: no framework dependencies, only oracledb.Connection.
"""
from typing import Optional
from oracledb import Connection


def create_book(db: Connection, book: dict) -> dict:
    """Insert a new book into the books table.
    Uses RETURNING clause to get the auto-generated ID.

    Args:
        db: Active Oracle connection to db_library
        book: Dict with keys: title, category, price, rating

    Returns:
        Dict with 'id' (new book ID) and 'status' ('created')
    """
    cursor = db.cursor()
    id_var = cursor.var(int)
    cursor.execute(
        """INSERT INTO books (title, category, price, rating)
           VALUES (:title, :category, :price, :rating)
           RETURNING id INTO :id""",
        book | {"id": id_var}
    )
    book_id = id_var.getvalue()[0]
    db.commit()
    cursor.close()
    return {"id": book_id, "status": "created"}


def list_books(db: Connection) -> list[dict]:
    """Fetch all books from the books table, ordered by ID.

    Args:
        db: Active Oracle connection to db_library

    Returns:
        List of dicts with keys: id, title, category, price, rating
    """
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, title, category, price, rating FROM books ORDER BY id"
    )
    columns = [col[0].lower() for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    return results
