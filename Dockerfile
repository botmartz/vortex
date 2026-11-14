# Multi-stage production Dockerfile for Botmartz VORTEX
# Stage 1: Build React 19 Studio Frontend
FROM oven/bun:1.1-alpine AS web-builder
WORKDIR /app/web
COPY web/package.json web/tsconfig.json web/vite.config.ts web/index.html ./
COPY web/src ./src
COPY web/public ./public
RUN bun install --frozen-lockfile || bun install
RUN bun run build

# Stage 2: Build Rust Crates & Python Wheel
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libsqlite3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain for native acceleration crates
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy Rust workspace
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
RUN cargo build --release --workspace

# Install Python requirements
COPY pyproject.toml ./
COPY python ./python
RUN pip install --no-cache-dir -e .

# Copy built frontend assets from web-builder
COPY --from=web-builder /app/python/botmartz_engine/api/static /app/python/botmartz_engine/api/static

# Environment defaults
ENV VORTEX_PORT=8420
ENV VORTEX_DATA_DIR=/app/data
VOLUME ["/app/data"]

EXPOSE 8420

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:8420/health || exit 1

CMD ["uvicorn", "botmartz_engine.api.server:app", "--host", "0.0.0.0", "--port", "8420"]
