"""
scraper.py - Web scraper for books.toscrape.com
Fetches book listings, navigates to detail pages to extract categories from breadcrumbs,
and loads data into db_scraping_raw with deduplication by SHA-256 hash(title+price).
"""
import requests
import hashlib
import time
from bs4 import BeautifulSoup
from typing import Optional

from scraper_service.src.config import BASE_URL, MAX_ITEMS
from scraper_service.src.loader import get_db_connection, load_raw, load_dlq
from scraper_service.src.logging_config import log


def compute_hash(title: str, price: float) -> str:
    """Generate SHA-256 hash from title+price for deduplication."""
    return hashlib.sha256(f"{title}{price}".encode()).hexdigest()


def wait_for_db(max_retries=60, delay=5):
    """Wait for Oracle database to become available with retry logic.
    Retries up to max_retries times with delay seconds between attempts.
    """
    for i in range(max_retries):
        try:
            conn = get_db_connection()
            conn.close()
            log.info("database_connected")
            return True
        except Exception as e:
            log.warning(f"database_not_ready, retry {i+1}/{max_retries}: {e}")
            time.sleep(delay)
    log.error("database_unreachable_after_retries")
    return False


def fetch_page(page: int = 1) -> Optional[str]:
    """Fetch a catalog page from books.toscrape.com.
    Returns HTML string or None on failure (logs to DLQ).
    """
    try:
        resp = requests.get(BASE_URL.format(page), timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        log.error("fetch_page_failed", error=str(e))
        load_dlq(None, str(e))
        return None


def parse_books(html: str) -> list:
    """Parse book data from catalog HTML.
    For each book, navigates to its detail page to extract category from breadcrumb.
    Returns list of dicts with: title, price, rating, availability, category, sk.
    """
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select(".product_pod")[:MAX_ITEMS]
    books = []
    for p in products:
        title = p.h3.a["title"]
        href = p.h3.a["href"]
        price_str = p.select_one(".price_color").text
        price = float("".join(c for c in price_str if c.isdigit() or c == "."))
        rating_class = p.select_one(".star-rating")["class"][1]
        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        availability = p.select_one(".instock.availability").text.strip() if p.select_one(".instock.availability") else "Unknown"

        # Extract category by navigating to detail page and parsing breadcrumb
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
        except Exception as e:
            log.warning(f"category_extract_failed: {e}")

        books.append({
            "title": title,
            "price": price,
            "rating": rating_map.get(rating_class, 0),
            "availability": availability,
            "category": category,
            "sk": compute_hash(title, price)
        })
    return books


def run():
    """Main scraper entry point. Waits for DB, fetches page 1, parses books, loads to RAW."""
    log.info("scraper_started")
    if not wait_for_db():
        return
    html = fetch_page(1)
    if not html:
        log.error("scraper_fetch_failed")
        return
    books = parse_books(html)
    log.info("books_parsed", count=len(books))
    conn = get_db_connection()
    try:
        for book in books:
            load_raw(book, conn)
        log.info("scraper_completed", loaded=len(books))
    finally:
        conn.close()


if __name__ == "__main__":
    run()
