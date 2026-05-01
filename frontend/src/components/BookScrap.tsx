/**
 * BookScrap - Displays scraped books from db_scraping_raw (RAW layer)
 * Shows all books fetched by the scraping DAG from books.toscrape.com
 * Includes category extracted from detail page breadcrumbs
 */
import React, { useEffect, useState } from "react";
import { listScrapedBooks, ScrapedBook } from "../api/books";

const BookScrap: React.FC = () => {
  const [books, setBooks] = useState<ScrapedBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Fetch scraped books on mount */
  useEffect(() => {
    listScrapedBooks()
      .then(setBooks)
      .catch((err: any) => setError(err.message || "Failed to fetch scraped books"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}>Loading scraped books...</div>;
  if (error) return <div style={{ color: "red", textAlign: "center" }}>Error: {error}</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Scraped Books ({books.length})</h2>
      {books.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40 }}>No scraped books yet. Run the scraping DAG.</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>#</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Title</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Category</th>
              <th style={{ padding: 10, textAlign: "right", borderBottom: "2px solid #ddd" }}>Price</th>
              <th style={{ padding: 10, textAlign: "center", borderBottom: "2px solid #ddd" }}>Rating</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Availability</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Scraped At</th>
            </tr>
          </thead>
          <tbody>
            {books.map((book, i) => (
              <tr key={book.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 10 }}>{i + 1}</td>
                <td style={{ padding: 10 }}>{book.title}</td>
                <td style={{ padding: 10 }}>{book.category || "-"}</td>
                <td style={{ padding: 10, textAlign: "right" }}>${book.price.toFixed(2)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>{"★".repeat(book.rating)}{"☆".repeat(5 - book.rating)}</td>
                <td style={{ padding: 10 }}>{book.availability}</td>
                <td style={{ padding: 10 }}>{book.scraped_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default BookScrap;
