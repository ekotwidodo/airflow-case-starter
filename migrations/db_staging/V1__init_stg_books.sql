CREATE TABLE stg_books (
    sk VARCHAR2(64) PRIMARY KEY,
    title VARCHAR2(255),
    category VARCHAR2(100),
    price NUMBER,
    rating NUMBER,
    source VARCHAR2(50),
    processed_at DATE
);
