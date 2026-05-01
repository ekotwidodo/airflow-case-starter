CREATE INDEX idx_fact_book_sk ON fact_books(book_sk);
CREATE INDEX idx_fact_created_at ON fact_books(created_at);
CREATE INDEX idx_stg_books_sk ON stg_books(sk);
