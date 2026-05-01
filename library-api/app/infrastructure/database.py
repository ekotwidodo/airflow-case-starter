"""
database.py - Database connection factory for Library API
Provides two connection factories:
  - get_connection(): Connects to db_library (OLTP for CRUD operations)
  - get_integrator_connection(): Connects to db_integrator (MART for dashboard queries)
All credentials come from environment variables with sensible defaults.
"""
import os
import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> oracledb.Connection:
    """Create connection to the library database (db_library).
    Used for CRUD operations on the books table.

    Returns:
        Active oracledb.Connection to db_library
    """
    host = os.getenv("DB_LIBRARY_HOST", "localhost")
    port = int(os.getenv("DB_LIBRARY_PORT", "1521"))
    service_name = os.getenv("DB_LIBRARY_SERVICE", "BOOKSDB")
    dsn = f"{host}:{port}/{service_name}"
    return oracledb.connect(
        user=os.getenv("DB_LIBRARY_USER", "library"),
        password=os.getenv("DB_LIBRARY_PASSWORD", "library"),
        dsn=dsn
    )


def get_integrator_connection() -> oracledb.Connection:
    """Create connection to the integrator database (db_integrator).
    Used for dashboard queries against fact_books and dim_book tables.

    Returns:
        Active oracledb.Connection to db_integrator
    """
    host = os.getenv("DB_INTEGRATOR_HOST", "localhost")
    port = int(os.getenv("DB_INTEGRATOR_PORT", "1521"))
    service_name = os.getenv("DB_INTEGRATOR_SERVICE", "BOOKSDB")
    dsn = f"{host}:{port}/{service_name}"
    return oracledb.connect(
        user=os.getenv("DB_INTEGRATOR_USER", "system"),
        password=os.getenv("DB_INTEGRATOR_PASSWORD", "oracle123"),
        dsn=dsn
    )
