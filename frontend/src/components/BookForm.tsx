import React, { useState } from "react";
import { createBook, BookCreate } from "../api/books";

interface BookFormProps {
  onSuccess: () => void;
}

const BookForm: React.FC<BookFormProps> = ({ onSuccess }) => {
  const [form, setForm] = useState<BookCreate>({
    title: "",
    category: "",
    price: 0,
    rating: 1,
  });
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = (): boolean => {
    const errs: string[] = [];
    if (!form.title.trim()) errs.push("Title is required");
    if (form.price <= 0) errs.push("Price must be greater than 0");
    if (form.rating < 1 || form.rating > 5) errs.push("Rating must be between 1 and 5");
    setErrors(errs);
    return errs.length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setSubmitError(null);
    try {
      await createBook(form);
      setForm({ title: "", category: "", price: 0, rating: 1 });
      setErrors([]);
      onSuccess();
    } catch (err: any) {
      const errorMsg = err.response?.data?.message || err.message || "Failed to create book";
      setSubmitError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 500, margin: "0 auto" }}>
      <h2>Create Book</h2>
      {errors.length > 0 && (
        <div style={{ color: "red", marginBottom: 10 }}>
          {errors.map((e, i) => <div key={i}>{e}</div>)}
        </div>
      )}
      {submitError && (
        <div style={{ color: "red", marginBottom: 10 }}>{submitError}</div>
      )}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 10 }}>
          <label>Title*</label><br />
          <input
            type="text"
            value={form.title}
            onChange={e => setForm({ ...form, title: e.target.value })}
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label>Category</label><br />
          <input
            type="text"
            value={form.category}
            onChange={e => setForm({ ...form, category: e.target.value })}
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label>Price*</label><br />
          <input
            type="number"
            step="0.01"
            value={form.price || ""}
            onChange={e => setForm({ ...form, price: parseFloat(e.target.value) || 0 })}
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label>Rating* (1-5)</label><br />
          <input
            type="number"
            min={1}
            max={5}
            value={form.rating}
            onChange={e => setForm({ ...form, rating: parseInt(e.target.value) || 1 })}
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <button type="submit" disabled={loading} style={{ padding: "10px 20px", cursor: loading ? "not-allowed" : "pointer" }}>
          {loading ? "Creating..." : "Create Book"}
        </button>
      </form>
    </div>
  );
};

export default BookForm;
