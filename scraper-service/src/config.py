"""
config.py - Scraper service configuration
Defines constants and DB config for the scraper service.
BASE_URL: books.toscrape.com catalog page template
MAX_ITEMS: Number of books to scrape per run (10 for demo)
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


# Catalog page URL template (page number inserted via .format())
BASE_URL = "http://books.toscrape.com/catalogue/page-{}.html"

# Maximum number of books to scrape per run
MAX_ITEMS = 10
