import pytest
from bs4 import BeautifulSoup
from scraper_service.src.scraper import parse_books, compute_hash

def test_parse_books():
    html = """
    <html>
        <div class="product_pod">
            <h3><a title="Test Book">Test</a></h3>
            <p class="price_color">£19.99</p>
            <p class="star-rating Three"></p>
            <p class="instock availability">In stock</p>
        </div>
        <div class="product_pod">
            <h3><a title="Another Book">Another</a></h3>
            <p class="price_color">£25.50</p>
            <p class="star-rating Five"></p>
        </div>
    </html>
    """
    books = parse_books(html)
    assert len(books) == 2
    assert books[0]["title"] == "Test Book"
    assert books[0]["price"] == 19.99
    assert books[0]["rating"] == 3
    assert books[1]["rating"] == 5

def test_parse_books_empty():
    books = parse_books("<html></html>")
    assert len(books) == 0

def test_compute_hash_idempotent():
    h1 = compute_hash("Book A", 10.0)
    h2 = compute_hash("Book A", 10.0)
    assert h1 == h2
    assert len(h1) == 64
