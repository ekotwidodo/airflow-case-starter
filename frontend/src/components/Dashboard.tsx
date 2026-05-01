/**
 * Dashboard - Analytics view powered by db_integrator (MART layer)
 * Displays KPIs, rating distribution, source distribution, category stats, and recent books
 * Data comes from fact_books and dim_book tables after staging + mart DAGs run
 */
import React, { useEffect, useState } from "react";
import axios from "axios";

/** Rating distribution: count of books per rating level (1-5) */
interface RatingDist {
  rating: number;
  count: number;
}

/** Source distribution: count of books per source (library vs scraper) */
interface SourceDist {
  source: string;
  count: number;
}

/** Category stats: book count per category (price removed per requirements) */
interface CategoryStat {
  category: string;
  count: number;
  avg_price: number;
}

/** Recent book entry for the "Recent Books" table */
interface RecentBook {
  title: string;
  price: number;
  rating: number;
  source: string;
  created_at: string;
}

/** Full dashboard response from /api/v1/dashboard */
interface DashboardData {
  total_books: number;
  total_categories: number;
  avg_price: number;
  rating_distribution: RatingDist[];
  source_distribution: SourceDist[];
  category_stats: CategoryStat[];
  recent_books: RecentBook[];
}

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Fetch dashboard data on mount */
  useEffect(() => {
    axios
      .get<DashboardData>("/api/v1/dashboard")
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div style={{ padding: 20 }}>Loading dashboard...</div>;
  if (error) return <div style={{ padding: 20, color: "red" }}>Error: {error}</div>;
  if (!data) return null;

  /** Calculate max values for bar chart scaling */
  const maxRatingCount = Math.max(...data.rating_distribution.map((r) => r.count), 1);
  const maxCategoryCount = Math.max(...data.category_stats.map((c) => c.count), 1);
  const maxSourceCount = Math.max(...data.source_distribution.map((s) => s.count), 1);

  return (
    <div style={{ padding: 20 }}>
      <h2 style={{ marginBottom: 20 }}>Data Mart Dashboard</h2>

      {/* KPI Cards: Total Books, Categories, Avg Price */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 30 }}>
        <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 8px", color: "#666", fontSize: 14 }}>Total Books</h3>
          <p style={{ margin: 0, fontSize: 32, fontWeight: "bold" }}>{data.total_books}</p>
        </div>
        <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 8px", color: "#666", fontSize: 14 }}>Categories</h3>
          <p style={{ margin: 0, fontSize: 32, fontWeight: "bold" }}>{data.total_categories}</p>
        </div>
        <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 8px", color: "#666", fontSize: 14 }}>Avg Price</h3>
          <p style={{ margin: 0, fontSize: 32, fontWeight: "bold" }}>${data.avg_price.toFixed(2)}</p>
        </div>
      </div>

      {/* Two-column layout: Rating+Source Distribution | Top Categories */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 30 }}>
        {/* Rating Distribution + Source Distribution panel */}
        <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 16px" }}>Rating Distribution</h3>
          {data.rating_distribution.map((r) => (
            <div key={r.rating} style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={{ width: 60, fontWeight: "bold" }}>{r.rating} Star</span>
              <div style={{ flex: 1, background: "#ddd", borderRadius: 4, height: 24, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${(r.count / maxRatingCount) * 100}%`,
                    background: "#4a90d9",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    paddingLeft: 8,
                    color: "#fff",
                    fontSize: 12,
                    minWidth: r.count > 0 ? 30 : 0
                  }}
                >
                  {r.count}
                </div>
              </div>
            </div>
          ))}
          {/* Source Distribution: Library vs Scraping */}
          <h3 style={{ margin: "24px 0 16px" }}>Source Distribution</h3>
          {data.source_distribution.map((s) => (
            <div key={s.source} style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={{ width: 80, fontWeight: "bold", fontSize: 13 }}>{s.source}</span>
              <div style={{ flex: 1, background: "#ddd", borderRadius: 4, height: 24, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${(s.count / maxSourceCount) * 100}%`,
                    background: s.source === "library" ? "#5cb85c" : "#f0ad4e",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    paddingLeft: 8,
                    color: "#fff",
                    fontSize: 12,
                    minWidth: s.count > 0 ? 30 : 0
                  }}
                >
                  {s.count}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Top Categories: count only, no price */}
        <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
          <h3 style={{ margin: "0 0 16px" }}>Top Categories</h3>
          {data.category_stats.map((c) => (
            <div key={c.category} style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={{ width: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.category}</span>
              <div style={{ flex: 1, background: "#ddd", borderRadius: 4, height: 24, overflow: "hidden", margin: "0 10px" }}>
                <div
                  style={{
                    width: `${(c.count / maxCategoryCount) * 100}%`,
                    background: "#5cb85c",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    paddingLeft: 8,
                    color: "#fff",
                    fontSize: 12,
                    minWidth: c.count > 0 ? 30 : 0
                  }}
                >
                  {c.count} books
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Books table */}
      <div style={{ background: "#f5f5f5", padding: 20, borderRadius: 8 }}>
        <h3 style={{ margin: "0 0 16px" }}>Recent Books</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #333" }}>
              <th style={{ textAlign: "left", padding: "8px 4px" }}>Title</th>
              <th style={{ textAlign: "right", padding: "8px 4px" }}>Price</th>
              <th style={{ textAlign: "center", padding: "8px 4px" }}>Rating</th>
              <th style={{ textAlign: "left", padding: "8px 4px" }}>Source</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_books.map((b, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #ddd" }}>
                <td style={{ padding: "8px 4px" }}>{b.title}</td>
                <td style={{ padding: "8px 4px", textAlign: "right" }}>${b.price.toFixed(2)}</td>
                <td style={{ padding: "8px 4px", textAlign: "center" }}>{b.rating}</td>
                <td style={{ padding: "8px 4px" }}>{b.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Dashboard;
