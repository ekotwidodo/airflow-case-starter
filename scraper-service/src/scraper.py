"""
scraper.py - Web scraper for books.toscrape.com
Random scraping strategy:
  1. Pick a random page from 1-50
  2. Scrape all 20 books from that page
  3. Randomly select 8 books
  4. Load selected books into db_scraping_raw with deduplication
"""
import requests
import hashlib
import time
import random
from bs4 import BeautifulSoup
from typing import Optional

from scraper_service.src.config import BASE_URL, TOTAL_PAGES, SAMPLE_SIZE
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


def fetch_page(page: int) -> Optional[str]:
    """Fetch a catalog page from books.toscrape.com.
    Page 1 uses index.html, pages 2-50 use catalogue/page-N.html.

    Args:
        page: Page number (1-50)

    Returns:
        HTML string or None on failure (logs to DLQ)
    """
    try:
        if page == 1:
            url = "https://books.toscrape.com/index.html"
        else:
            url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        log.error("fetch_page_failed", page=page, error=str(e))
        load_dlq(None, str(e))
        return None


def parse_books(html: str) -> list:
    """Parse all book data from catalog HTML.
    For each book, navigates to its detail page to extract category from breadcrumb.

    Args:
        html: Raw HTML from catalog page

    Returns:
        List of dicts with: title, price, rating, availability, category, sk
    """
    soup = BeautifulSoup(html, "html.parser")
    products = soup.select(".product_pod")
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
                detail_url = "https://books.toscrape.com/" + href.replace("../", "")
            else:
                detail_url = "https://books.toscrape.com/catalogue/" + href
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
    """Main scraper entry point.
    Strategy:
      1. Wait for database
      2. Pick random page (1-50)
      3. Fetch and parse all books from that page
      4. Randomly select SAMPLE_SIZE books (default: 8)
      5. Load selected books to RAW with deduplication
    """
    log.info("scraper_started")
    if not wait_for_db():
        return

    # Step 1: Pick random page from 1 to TOTAL_PAGES
    page = random.randint(1, TOTAL_PAGES)
    log.info("random_page_selected", page=page)

    # Step 2: Fetch the page
    html = fetch_page(page)
    if not html:
        log.error("scraper_fetch_failed")
        return

    # Step 3: Parse all books (up to 20 per page)
    all_books = parse_books(html)
    log.info("books_parsed", total=len(all_books))

    # Step 4: Randomly select SAMPLE_SIZE books
    selected = random.sample(all_books, min(SAMPLE_SIZE, len(all_books)))
    log.info("books_randomly_selected", count=len(selected))

    # Step 5: Load to database
    conn = get_db_connection()
    try:
        loaded = 0
        for book in selected:
            if load_raw(book, conn):
                loaded += 1
        log.info("scraper_completed", page=page, selected=len(selected), loaded=loaded)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
