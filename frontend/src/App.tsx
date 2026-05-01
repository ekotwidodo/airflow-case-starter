/**
 * App - Main application component
 * Renders navigation and switches between views:
 * Book List (CRUD), Book Scrap (raw scraped data), Book All (integrator), Dashboard
 */
import React, { useState } from "react";
import BookList from "./components/BookList";
import BookScrap from "./components/BookScrap";
import BookAll from "./components/BookAll";
import Dashboard from "./components/Dashboard";

/** Available views in the application */
type View = "list" | "scrap" | "all" | "dashboard";

const App: React.FC = () => {
  const [view, setView] = useState<View>("list");

  /** Generate navigation button styles based on active view */
  const navBtn = (label: string, v: View) => ({
    padding: "8px 16px",
    marginRight: 10,
    background: view === v ? "#333" : "#eee",
    color: view === v ? "#fff" : "#333",
    border: "none",
    cursor: "pointer" as const
  });

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 20, fontFamily: "Arial, sans-serif" }}>
      <header style={{ marginBottom: 30, borderBottom: "2px solid #333", paddingBottom: 15 }}>
        <h1 style={{ margin: 0 }}>Books Ecosystem</h1>
        <nav style={{ marginTop: 10 }}>
          <button onClick={() => setView("list")} style={navBtn("Book List", "list")}>Book List</button>
          <button onClick={() => setView("scrap")} style={navBtn("Book Scrap", "scrap")}>Book Scrap</button>
          <button onClick={() => setView("all")} style={navBtn("Book All", "all")}>Book All</button>
          <button onClick={() => setView("dashboard")} style={navBtn("Dashboard", "dashboard")}>Dashboard</button>
        </nav>
      </header>
      <main>
        {view === "list" && <BookList />}
        {view === "scrap" && <BookScrap />}
        {view === "all" && <BookAll />}
        {view === "dashboard" && <Dashboard />}
      </main>
    </div>
  );
};

export default App;
