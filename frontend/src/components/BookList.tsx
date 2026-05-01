/**
 * BookList - CRUD view for library books (db_library)
 * Features: filter by category/rating, pagination, add/edit/delete via modals
 * Column "#" shows row order number, not database ID
 */
import React, { useEffect, useState } from "react";
import { listBooks, updateBook, deleteBook, createBook, Book, BookCreate } from "../api/books";

const BookList: React.FC = () => {
  /** State: books list, loading, error, filters, pagination */
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [ratingFilter, setRatingFilter] = useState<number | "">("");
  const [page, setPage] = useState(1);
  const pageSize = 10;

  /** State: edit modal */
  const [editingBook, setEditingBook] = useState<Book | null>(null);
  const [editForm, setEditForm] = useState<BookCreate>({ title: "", category: "", price: 0, rating: 1 });

  /** State: create modal */
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<BookCreate>({ title: "", category: "", price: 0, rating: 1 });

  /** Fetch all books from library API */
  const fetchBooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listBooks();
      setBooks(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch books");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBooks(); }, []);

  /** Filter books by category (case-insensitive) and minimum rating */
  const filtered = books.filter(b => {
    if (categoryFilter && (!b.category || !b.category.toLowerCase().includes(categoryFilter.toLowerCase()))) return false;
    if (ratingFilter && b.rating < ratingFilter) return false;
    return true;
  });
  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  /** Open edit modal with book data pre-filled */
  const handleEdit = (book: Book) => {
    setEditingBook(book);
    setEditForm({ title: book.title, category: book.category || "", price: book.price, rating: book.rating });
  };

  /** Save edited book via PUT API, then refresh list */
  const handleSaveEdit = async () => {
    if (!editingBook) return;
    try {
      await updateBook(editingBook.id, editForm);
      setEditingBook(null);
      fetchBooks();
    } catch (err: any) {
      setError(err.message || "Failed to update book");
    }
  };

  /** Delete book via DELETE API after confirmation, then refresh list */
  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this book?")) return;
    try {
      await deleteBook(id);
      fetchBooks();
    } catch (err: any) {
      setError(err.message || "Failed to delete book");
    }
  };

  /** Create new book via POST API, close modal, then refresh list */
  const handleSaveCreate = async () => {
    try {
      await createBook(createForm);
      setShowCreate(false);
      setCreateForm({ title: "", category: "", price: 0, rating: 1 });
      fetchBooks();
    } catch (err: any) {
      setError(err.message || "Failed to create book");
    }
  };

  if (loading) return <div style={{ textAlign: "center", padding: 40 }}>Loading books...</div>;
  if (error) return <div style={{ color: "red", textAlign: "center" }}>Error: {error}</div>;

  return (
    <div>
      {/* Filter bar and Add Book button */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flex: 1 }}>
          <input type="text" placeholder="Filter by category..." value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} style={{ padding: 8, flex: 1 }} />
          <select value={ratingFilter} onChange={e => setRatingFilter(e.target.value ? parseInt(e.target.value) : "")} style={{ padding: 8 }}>
            <option value="">All Ratings</option>
            {[1,2,3,4,5].map(r => <option key={r} value={r}>{r}+</option>)}
          </select>
          <button onClick={fetchBooks} style={{ padding: "8px 16px" }}>Refresh</button>
        </div>
        <button onClick={() => setShowCreate(true)} style={{ padding: "8px 16px", background: "#4a90d9", color: "#fff", border: "none", cursor: "pointer" }}>+ Add Book</button>
      </div>

      {/* Books table with row numbers, edit/delete actions */}
      {paginated.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40 }}>No books found.</div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>#</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Title</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Category</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Price</th>
              <th style={{ padding: 10, textAlign: "left", borderBottom: "2px solid #ddd" }}>Rating</th>
              <th style={{ padding: 10, textAlign: "center", borderBottom: "2px solid #ddd" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((book, idx) => (
              <tr key={book.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: 10 }}>{(page - 1) * pageSize + idx + 1}</td>
                <td style={{ padding: 10 }}>{book.title}</td>
                <td style={{ padding: 10 }}>{book.category || "-"}</td>
                <td style={{ padding: 10 }}>${book.price.toFixed(2)}</td>
                <td style={{ padding: 10 }}>{"★".repeat(book.rating)}{"☆".repeat(5 - book.rating)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>
                  <span onClick={() => handleEdit(book)} style={{ cursor: "pointer", marginRight: 12, fontSize: 18, color: "#4a90d9" }} title="Edit">&#9998;</span>
                  <span onClick={() => handleDelete(book.id)} style={{ cursor: "pointer", fontSize: 18, color: "#e74c3c" }} title="Delete">&#10005;</span>
                </td>
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

      {/* Edit Book Modal - symmetrical with Create modal */}
      {editingBook && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#fff", padding: 30, borderRadius: 8, width: "100%", maxWidth: 450, boxSizing: "border-box" }}>
            <h3 style={{ margin: "0 0 20px" }}>Edit Book</h3>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Title</label>
              <input type="text" value={editForm.title} onChange={e => setEditForm({...editForm, title: e.target.value})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Category</label>
              <input type="text" value={editForm.category} onChange={e => setEditForm({...editForm, category: e.target.value})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Price</label>
              <input type="number" step="0.01" value={editForm.price} onChange={e => setEditForm({...editForm, price: parseFloat(e.target.value)})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Rating (1-5)</label>
              <input type="number" min="1" max="5" value={editForm.rating} onChange={e => setEditForm({...editForm, rating: parseInt(e.target.value)})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setEditingBook(null)} style={{ padding: "8px 20px" }}>Cancel</button>
              <button onClick={handleSaveEdit} style={{ padding: "8px 20px", background: "#4a90d9", color: "#fff", border: "none" }}>Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Book Modal - symmetrical with Edit modal */}
      {showCreate && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#fff", padding: 30, borderRadius: 8, width: "100%", maxWidth: 450, boxSizing: "border-box" }}>
            <h3 style={{ margin: "0 0 20px" }}>Add Book</h3>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Title</label>
              <input type="text" value={createForm.title} onChange={e => setCreateForm({...createForm, title: e.target.value})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Category</label>
              <input type="text" value={createForm.category} onChange={e => setCreateForm({...createForm, category: e.target.value})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Price</label>
              <input type="number" step="0.01" value={createForm.price} onChange={e => setCreateForm({...createForm, price: parseFloat(e.target.value)})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>Rating (1-5)</label>
              <input type="number" min="1" max="5" value={createForm.rating} onChange={e => setCreateForm({...createForm, rating: parseInt(e.target.value)})} style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowCreate(false)} style={{ padding: "8px 20px" }}>Cancel</button>
              <button onClick={handleSaveCreate} style={{ padding: "8px 20px", background: "#4a90d9", color: "#fff", border: "none" }}>Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookList;
