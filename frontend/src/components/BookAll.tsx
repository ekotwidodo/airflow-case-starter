/**
 * BookAll - Displays merged books from db_integrator (MART layer)
 * Shows the final deduplicated data after staging + mart DAGs run
 * Includes source column (library vs scraper) to track data origin
 */
import React, { useEffect, useState } from "react";
import { listIntegratorBooks, IntegratorBook } from "../api/books";

const BookAll: React.FC = () => {
  const [books, setBooks] = useState<IntegratorBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Fetch integrator books on mount */
  useEffect(() => {
    listIntegratorBooks()
      .then(setBooks)
      .catch((err: any) => setError(err.message || "Failed to fetch integrator books"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}>Loading integrator books...</div>;
  if (error) return <div style={{ color: "red", textAlign: "center" }}>Error: {error}</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>All Books - Integrator ({books.length})</h2>
      {books.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40 }}>No books in integrator. Run staging and mart DAGs.</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>#</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Title</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Category</th>
              <th style={{ padding: 10, textAlign: "right", borderBottom: "2px solid #ddd" }}>Price</th>
              <th style={{ padding: 10, textAlign: "center", borderBottom: "2px solid #ddd" }}>Rating</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Source</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Created At</th>
            </tr>
          </thead>
          <tbody>
            {books.map((book, i) => (
              <tr key={book.sk} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 10 }}>{i + 1}</td>
                <td style={{ padding: 10 }}>{book.title}</td>
                <td style={{ padding: 10 }}>{book.category || "-"}</td>
                <td style={{ padding: 10, textAlign: "right" }}>${book.price.toFixed(2)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>{"★".repeat(book.rating)}{"☆".repeat(5 - book.rating)}</td>
                <td style={{ padding: 10 }}>{book.source}</td>
                <td style={{ padding: 10 }}>{book.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default BookAll;
