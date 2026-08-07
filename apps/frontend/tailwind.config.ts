import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // One accent colour per retrieval strategy, used consistently across
        // the UI so you can see at a glance which path answered a question.
        strategy: {
          sql: "#2563eb",
          vector: "#7c3aed",
          opensearch: "#059669",
          hybrid: "#ea580c",
        },
      },
    },
  },
  plugins: [],
};

export default config;
