CREATE TABLE dlq_books (
    id NUMBER,
    payload CLOB,
    error_message VARCHAR2(500),
    created_at DATE
);
