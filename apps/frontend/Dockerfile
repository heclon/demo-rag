# Build from the REPO ROOT so packages/shared-types is in context:
#   docker build -f apps/frontend/Dockerfile -t demo-rag-web .
FROM node:22-slim AS builder

WORKDIR /repo

# Copy manifests first so dependency install is cached independently of source.
COPY apps/frontend/package.json apps/frontend/package-lock.json ./apps/frontend/
COPY packages/shared-types/package.json ./packages/shared-types/
RUN npm --prefix apps/frontend ci --no-audit --no-fund

COPY packages/shared-types ./packages/shared-types
COPY apps/frontend ./apps/frontend

# The API URL is baked into the client bundle at build time (NEXT_PUBLIC_*),
# so it is an ARG rather than a runtime ENV.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm --prefix apps/frontend run build


FROM node:22-slim AS runtime

RUN useradd --create-home --uid 1001 appuser
WORKDIR /repo

COPY --from=builder --chown=appuser:appuser /repo /repo

ENV NODE_ENV=production
USER appuser
EXPOSE 3000

CMD ["npm", "--prefix", "apps/frontend", "run", "start"]
