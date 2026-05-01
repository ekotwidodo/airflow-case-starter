/**
 * BookScrap - Displays scraped books from db_scraping_raw (RAW layer)
 * Shows all books fetched by the scraping DAG from books.toscrape.com
 * Includes category extracted from detail page breadcrumbs
 * Features: search by title, filter by category/rating, pagination
 */
import React, { useEffect, useState } from "react";
import { listScrapedBooks, ScrapedBook } from "../api/books";

const BookScrap: React.FC = () => {
  /** State: books list, loading, error */
  const [books, setBooks] = useState<ScrapedBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** State: search and filter */
  const [titleSearch, setTitleSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [ratingFilter, setRatingFilter] = useState<number | "">("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  /** Fetch scraped books on mount */
  useEffect(() => {
    listScrapedBooks()
      .then(setBooks)
      .catch((err: any) => setError(err.message || "Failed to fetch scraped books"))
      .finally(() => setLoading(false));
  }, []);

  /** Reset to page 1 when filters change */
  useEffect(() => { setPage(1); }, [titleSearch, categoryFilter, ratingFilter]);

  /** Filter books by title, category, and minimum rating */
  const filtered = books.filter(b => {
    if (titleSearch && !b.title.toLowerCase().includes(titleSearch.toLowerCase())) return false;
    if (categoryFilter && (!b.category || !b.category.toLowerCase().includes(categoryFilter.toLowerCase()))) return false;
    if (ratingFilter && b.rating < ratingFilter) return false;
    return true;
  });
  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}>Loading scraped books...</div>;
  if (error) return <div style={{ color: "red", textAlign: "center" }}>Error: {error}</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Scraped Books</h2>

      {/* Filter bar: title search, category filter, rating filter, refresh, reset */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <input type="text" placeholder="Search by title..." value={titleSearch} onChange={e => setTitleSearch(e.target.value)} style={{ padding: 8, flex: 1, minWidth: 150 }} />
        <input type="text" placeholder="Filter by category..." value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} style={{ padding: 8, width: 160 }} />
        <select value={ratingFilter} onChange={e => setRatingFilter(e.target.value ? parseInt(e.target.value) : "")} style={{ padding: 8 }}>
          <option value="">All Ratings</option>
          {[1,2,3,4,5].map(r => <option key={r} value={r}>{r}+ Star</option>)}
        </select>
        <button onClick={() => listScrapedBooks().then(setBooks)} style={{ padding: "8px 16px" }}>Refresh</button>
        <button onClick={() => { setTitleSearch(""); setCategoryFilter(""); setRatingFilter(""); }} style={{ padding: "8px 16px" }}>Reset</button>
      </div>
      <div style={{ marginBottom: 10, color: "#666", fontSize: 13 }}>Showing {paginated.length} of {filtered.length} books</div>

      {/* Books table */}
      {paginated.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40 }}>No scraped books found. Run the scraping DAG.</div>
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
            {paginated.map((book, idx) => (
              <tr key={book.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 10 }}>{(page - 1) * pageSize + idx + 1}</td>
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

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div style={{ marginTop: 20, display: "flex", justifyContent: "center", gap: 10 }}>
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} style={{ padding: "5px 15px" }}>Previous</button>
          <span style={{ padding: "5px 10px" }}>Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: "5px 15px" }}>Next</button>
        </div>
      )}
    </div>
  );
};

export default BookScrap;
