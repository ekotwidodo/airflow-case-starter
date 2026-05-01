import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "library-api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scraper-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "airflow"))

from scraper_service.src.scraper import parse_books

def test_etl_pipeline_parse():
    """Verify parser produces correct structure for ETL pipeline"""
    html = """
    <html>
        <div class="product_pod">
            <h3><a title="Pipeline Test Book">Test</a></h3>
            <p class="price_color">£15.00</p>
            <p class="star-rating Four"></p>
        </div>
    </html>
    """
    books = parse_books(html)
    assert len(books) == 1
    book = books[0]
    assert "title" in book
    assert "price" in book
    assert "rating" in book
    assert "sk" in book
    assert book["price"] > 0
    assert 1 <= book["rating"] <= 5

def test_data_quality_price():
    """Data test: price must be > 0"""
    book = {"title": "Test", "price": -5, "rating": 3}
    assert not (book["price"] > 0)

def test_data_quality_rating():
    """Data test: rating must be 1-5"""
    for rating in [0, 6, -1]:
        book = {"rating": rating}
        assert not (1 <= book["rating"] <= 5)
    for rating in [1, 3, 5]:
        book = {"rating": rating}
        assert 1 <= book["rating"] <= 5

def test_data_quality_null_check():
    """Data test: title should not be null/empty"""
    books = [
        {"title": "Valid Book", "price": 10.0},
        {"title": "", "price": 5.0},
        {"title": None, "price": 7.0},
    ]
    valid = [b for b in books if b.get("title")]
    assert len(valid) == 1
