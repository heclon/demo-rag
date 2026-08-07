/**
 * Typed API client for the FastAPI backend.
 *
 * Every function returns the shared types from @demo-rag/shared-types, so a
 * backend schema change that isn't mirrored there fails typecheck here.
 */
import type {
  AgentQueryResponse,
  IngestResponse,
  OpenSearchResponse,
  ProductListResponse,
  ProductWithReviews,
  SqlSearchResponse,
  VectorSearchResponse,
} from "@demo-rag/shared-types";

/**
 * The browser and the Next.js server reach the API over different hostnames
 * when running under docker compose: the browser uses the published port on
 * localhost, while server components resolve the `api` service on the compose
 * network. Outside Docker both are unset and collapse to the same localhost
 * URL, so local dev needs no configuration.
 */
const BROWSER_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SERVER_BASE = process.env.API_URL_INTERNAL ?? BROWSER_BASE;

export const API_BASE = typeof window === "undefined" ? SERVER_BASE : BROWSER_BASE;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    // A network-level failure almost always means the API isn't running —
    // say so plainly rather than surfacing "Failed to fetch".
    throw new ApiError(
      `Could not reach the API at ${API_BASE}. Is the backend running?`,
      0,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* response had no JSON body; keep statusText */
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export interface ProductFilters {
  limit?: number;
  offset?: number;
  category?: string;
  brand?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  q?: string;
}

export const api = {
  listProducts(filters: ProductFilters = {}): Promise<ProductListResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== "" && value !== null) {
        params.set(key, String(value));
      }
    }
    const qs = params.toString();
    return request<ProductListResponse>(`/products${qs ? `?${qs}` : ""}`);
  },

  getProduct(id: number): Promise<ProductWithReviews> {
    return request<ProductWithReviews>(`/products/${id}`);
  },

  getCategories(): Promise<string[]> {
    return request<string[]>("/products/categories");
  },

  getBrands(): Promise<string[]> {
    return request<string[]>("/products/brands");
  },

  searchSql(question: string): Promise<SqlSearchResponse> {
    return post<SqlSearchResponse>("/search/sql", { question });
  },

  searchVector(query: string, top_k = 5): Promise<VectorSearchResponse> {
    return post<VectorSearchResponse>("/search/vector", { query, top_k });
  },

  searchOpenSearch(query: string, top_k = 5): Promise<OpenSearchResponse> {
    return post<OpenSearchResponse>("/search/opensearch", { query, top_k });
  },

  searchOpenSearchHybrid(query: string, top_k = 5): Promise<OpenSearchResponse> {
    return post<OpenSearchResponse>("/search/opensearch/hybrid", { query, top_k });
  },

  askAgent(question: string): Promise<AgentQueryResponse> {
    return post<AgentQueryResponse>("/agent/query", { question });
  },

  ingest(): Promise<IngestResponse> {
    return post<IngestResponse>("/ingest", {});
  },
};
