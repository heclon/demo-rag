/**
 * Shared TypeScript types for demo-rag.
 * Mirrors the Pydantic schemas in services/api/app/schemas so the frontend
 * and backend never drift silently — if you change one, change both.
 */

export type RetrievalStrategy = "sql" | "vector" | "opensearch" | "hybrid";

export interface Product {
  id: number;
  title: string;
  description: string;
  category: string;
  brand: string;
  price: number;
  rating: number;
  inventory: number;
  specifications: Record<string, string>;
  created_at: string;
}

export interface Review {
  id: number;
  product_id: number;
  author: string;
  rating: number;
  title: string;
  body: string;
  created_at: string;
}

export interface ProductWithReviews extends Product {
  reviews: Review[];
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface SqlSearchRequest {
  question: string;
}

export interface SqlSearchResponse {
  question: string;
  generated_sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  answer: string;
  strategy: "sql";
}

export interface VectorSearchRequest {
  query: string;
  top_k?: number;
}

export interface VectorMatch {
  product: Product;
  score: number;
  matched_field: "description" | "specifications";
}

export interface VectorSearchResponse {
  query: string;
  matches: VectorMatch[];
  answer: string;
  strategy: "vector";
}

export interface OpenSearchRequest {
  query: string;
  top_k?: number;
}

export interface OpenSearchHit {
  product_id: number;
  product_title: string;
  review_snippet: string;
  score: number;
}

export interface OpenSearchResponse {
  query: string;
  hits: OpenSearchHit[];
  answer: string;
  strategy: "opensearch";
}

export interface AgentQueryRequest {
  question: string;
}

export interface AgentStep {
  tool: RetrievalStrategy;
  reasoning: string;
}

export interface AgentQueryResponse {
  question: string;
  strategy: RetrievalStrategy;
  answer: string;
  sql?: SqlSearchResponse | null;
  vector?: VectorSearchResponse | null;
  opensearch?: OpenSearchResponse | null;
  /** Reasoning trace — shown in the demo UI as a collapsible "how the agent decided" panel. */
  trace: AgentStep[];
}

export interface IngestResponse {
  products_ingested: number;
  reviews_ingested: number;
  embeddings_created: number;
  opensearch_docs_indexed: number;
}
