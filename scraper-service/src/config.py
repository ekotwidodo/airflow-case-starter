"""
config.py - Scraper service configuration
Defines constants and DB config for the scraper service.

BASE_URL: books.toscrape.com catalog page template (page 1 uses index.html)
TOTAL_PAGES: Total number of catalog pages available (50)
SAMPLE_SIZE: Number of books to randomly select per run (8 out of 20)
"""
import os
from dotenv import load_dotenv

load_dotenv()


def get_db_config():
    """Return Oracle DB connection parameters for db_scraping_raw.
    Reads from environment variables with defaults for local development.
    """
    host = os.getenv("SCRAPING_RAW_HOST", "localhost")
    port = os.getenv("SCRAPING_RAW_PORT", "1521")
    service = os.getenv("SCRAPING_RAW_SERVICE", "BOOKSDB")
    return {
        "user": os.getenv("SCRAPING_RAW_USER", "raw_user"),
        "password": os.getenv("SCRAPING_RAW_PASSWORD", "raw_pass"),
        "dsn": f"{host}:{port}/{service}"
    }


# Total catalog pages on books.toscrape.com
TOTAL_PAGES = 50

# Number of books to randomly select per scraping run
SAMPLE_SIZE = 8
