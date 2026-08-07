import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "demo-rag — RAG techniques over a tiny shop",
  description:
    "Demo of SQL RAG, pgvector semantic search, OpenSearch review search, and agentic retrieval routing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-8 text-xs text-slate-400">
          Demo application — SQL RAG, pgvector, OpenSearch, and an agent that
          routes between them.
        </footer>
      </body>
    </html>
  );
}
