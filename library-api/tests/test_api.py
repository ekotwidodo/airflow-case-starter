import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_book_success():
    response = client.post("/api/v1/books", json={
        "title": "Test Book",
        "category": "Fiction",
        "price": 19.99,
        "rating": 4
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert "id" in data

def test_create_book_invalid_price():
    response = client.post("/api/v1/books", json={
        "title": "Test Book",
        "price": -5,
        "rating": 4
    })
    assert response.status_code == 422

def test_create_book_missing_title():
    response = client.post("/api/v1/books", json={
        "price": 10.0,
        "rating": 3
    })
    assert response.status_code == 422

def test_create_book_invalid_rating():
    response = client.post("/api/v1/books", json={
        "title": "Test Book",
        "price": 10.0,
        "rating": 6
    })
    assert response.status_code == 422

def test_list_books():
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
