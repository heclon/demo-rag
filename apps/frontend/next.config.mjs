/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The shared-types package is consumed as TypeScript source rather than a
  // build artifact, so Next must transpile it.
  transpilePackages: ["@demo-rag/shared-types"],
  outputFileTracingRoot: new URL("../../", import.meta.url).pathname,
};

export default nextConfig;
