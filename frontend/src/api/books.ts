/**
 * books.ts - API client for all book-related endpoints
 * Communicates with Library API (FastAPI) via Nginx proxy at /api/v1/
 * Covers: library CRUD, scraped books, integrator books
 */
import axios, { AxiosError } from "axios";

const API_BASE = "/api/v1";

/** Book from library database (db_library) */
export interface Book {
  id: number;
  title: string;
  category: string | null;
  price: number;
  rating: number;
}

/** Payload for creating/updating a book */
export interface BookCreate {
  title: string;
  category?: string;
  price: number;
  rating: number;
}

/** Response from create book endpoint */
export interface CreateBookResponse {
  id: number;
  status: string;
}

/** Scraped book from raw database (db_scraping_raw) */
export interface ScrapedBook {
  id: number;
  title: string;
  price: number;
  rating: number;
  availability: string;
  category: string | null;
  scraped_at: string;
}

/** Integrator book from mart database (db_integrator) */
export interface IntegratorBook {
  sk: string;
  title: string;
  price: number;
  rating: number;
  category: string | null;
  source: string;
  created_at: string;
}

/** Create a new book in library database */
export const createBook = async (data: BookCreate): Promise<CreateBookResponse> => {
  const response = await axios.post<CreateBookResponse>(`${API_BASE}/books`, data);
  return response.data;
};

/** List all books from library database */
export const listBooks = async (params?: {
  category?: string;
  minRating?: number;
  page?: number;
}): Promise<Book[]> => {
  const response = await axios.get<Book[]>(`${API_BASE}/books`, { params });
  return response.data;
};

/** Update an existing book by ID */
export const updateBook = async (id: number, data: BookCreate): Promise<CreateBookResponse> => {
  const response = await axios.put<CreateBookResponse>(`${API_BASE}/books/${id}`, data);
  return response.data;
};

/** Delete a book by ID */
export const deleteBook = async (id: number): Promise<{ id: number; status: string }> => {
  const response = await axios.delete<{ id: number; status: string }>(`${API_BASE}/books/${id}`);
  return response.data;
};

/** List all scraped books from raw database */
export const listScrapedBooks = async (): Promise<ScrapedBook[]> => {
  const response = await axios.get<ScrapedBook[]>(`${API_BASE}/books/scraped`);
  return response.data;
};

/** List all books from integrator/mart database */
export const listIntegratorBooks = async (): Promise<IntegratorBook[]> => {
  const response = await axios.get<IntegratorBook[]>(`${API_BASE}/books/integrator`);
  return response.data;
};
