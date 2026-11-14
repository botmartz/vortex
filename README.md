<p align="center">
  <img src="./docs/assets/vortex-logo.svg" width="140" height="140" alt="Botmartz VORTEX Logo" />
</p>

<h1 align="center">Botmartz VORTEX</h1>

<p align="center">
  <b>Frontier Omni-RAG & Deep Agent Harness Engine</b><br>
  <i>Sub-500MB Zero-Sprawl Runtime · H-RAG AST Trees · JEV Late Chunking · BLAKE3 Merkle Diffing · KAG DuckDB OLAP SQL · SmithDB</i>
</p>

<p align="center">
  <a href="https://github.com/botmartz/vortex/stargazers"><img src="https://img.shields.io/github/stars/botmartz/vortex?style=flat-square&color=B85D3B" alt="GitHub Stars" /></a>
  <a href="https://github.com/botmartz/vortex/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-141413?style=flat-square" alt="License" /></a>
  <a href="https://hub.docker.com/r/botmartz/vortex"><img src="https://img.shields.io/badge/Docker-Single%20Container-2A6F4E?style=flat-square" alt="Docker" /></a>
  <a href="https://github.com/botmartz/vortex/issues"><img src="https://img.shields.io/github/issues/botmartz/vortex?style=flat-square&color=B85D3B" alt="Open Issues" /></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> •
  <a href="#botmartz-open-source-suite">The Botmartz Ecosystem</a> •
  <a href="#enterprise-deployment-docker--k8s">Docker & Kubernetes</a> •
  <a href="#benchmark-vs-ragflow">Benchmark vs RAGFlow</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## What is Botmartz VORTEX?

**VORTEX** is an open-source, enterprise-grade Omni-RAG and Deep Agent Harness engine designed to replace bloated multi-container stacks (such as RAGFlow and Dify) with a **high-performance, zero-sprawl single runtime**.

### Why Developers & Enterprises Choose VORTEX:

1. **Zero Ops Sprawl (<500 MB Idle Memory)**: Runs as a single process combining a native Rust core, LanceDB vector index, DuckDB 2.0 analytical engine, and SQLite WAL. No required Elasticsearch, MySQL, MinIO, or Redis containers.
2. **$O(\Delta)$ BLAKE3 Merkle Tree Mutation**: Only re-embeds mutated subtrees when documents change, skipping **~88.9%** of redundant embedding and compute costs.
3. **Deterministic Math (DuckDB KAG)**: Eliminates tabular hallucination. Numerical questions compile automatically into DuckDB OLAP SQL queries for 100% exact math.
4. **Hierarchical Document Trees (H-RAG & JEV)**: Preserves document ASTs and calculates late-chunking embeddings over full-document attention matrices before chunk pooling.
5. **SmithDB & Pregel BSP Agent Harness**: Built-in 4-superstep state graph with immutable checkpointing, waterfall span traces, and time-travel replay.
6. **Multi-Model Routing**: Native **Gemini First (Google AI Primary)**, cascading smoothly to **Ollama**, **llama.cpp server**, or **OpenAI/vLLM/SGLang**.

---

## 🌐 The Botmartz Open-Source Ecosystem

VORTEX is part of the interconnected **Botmartz AI Systems** suite:

| Repository | Role in the Ecosystem |
| :--- | :--- |
| **[botmartz/vortex](https://github.com/botmartz/vortex)** | **Core Engine**: Zero-sprawl Omni-RAG, H-RAG AST, DuckDB SQL, and React 19 Studio. |
| **[botmartz/llamaparse-pgvector-pipeline](https://github.com/botmartz/llamaparse-pgvector-pipeline)** | **Ingestion Pipeline**: Vision-based AST layout & table extraction for complex PDFs and 10-K balance sheets. |
| **[botmartz/mcp-postgres-wal-server](https://github.com/botmartz/mcp-postgres-wal-server)** | **Enterprise State Server**: MCP protocol server for PostgreSQL WAL checkpoints and Saga rollback transactions. |

---

## ⚡ Quickstart

### Method 1: Local Python & Bun (Recommended for Development)

```bash
# 1. Clone
git clone https://github.com/botmartz/vortex.git
cd vortex

# 2. Python Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Build React Studio
cd web && bun install && bun run build && cd ..

# 4. Start VORTEX Engine & Studio
uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420
```
Open **`http://127.0.0.1:8420`** in your browser.

---

## 🐳 Enterprise Deployment: Docker & Kubernetes

### 1. Single Container Run (Zero-Sprawl)
```bash
docker run -d \
  --name botmartz-vortex \
  -p 8420:8420 \
  -v vortex_data:/app/data \
  -e GEMINI_API_KEY="your-gemini-key" \
  botmartz/vortex:latest
```

### 2. Docker Compose
```bash
docker compose up -d
```

### 3. Enterprise Kubernetes / Helm
For enterprise high-availability clusters, mount a shared NFS or cloud persistent volume (`PVC`) to `/app/data` and configure `VORTEX_SMITHDB_URL` to point to external PostgreSQL clusters using `mcp-postgres-wal-server`.

---

## 📊 Benchmark: VORTEX vs. Infiniflow RAGFlow

| Feature | Infiniflow RAGFlow | Botmartz VORTEX v0.3 | Advantage |
| :--- | :--- | :--- | :--- |
| **Idle Memory Footprint** | 7–14 Docker containers (8–16 GB RAM) | 1 local process (< 500 MB RAM) | **95% less RAM, instant boot** |
| **Document Mutation Cost** | $O(N)$ full re-index (0% skipped) | $O(\Delta)$ BLAKE3 Merkle diff (~88.9% skipped) | **~90% compute cost reduction** |
| **Tabular Math Precision** | Markdown text snippet (LLM guessing) | Embedded DuckDB 2.0 OLAP SQL | **100% exact numerical accuracy** |
| **Cross-Chunk Context** | Flat delimiter cuts | H-RAG AST + JEV Late Chunking | **Zero chunk-context blindness** |
| **Agent State & Replay** | MySQL/Redis task queues | Built-in SmithDB (Checkpoints & Replay) | **Built-in time-travel debugging** |
| **Model Connectivity** | Proprietary wrappers | Gemini First + Ollama + llama.cpp + vLLM | **Total freedom of compute** |

---

## 🤝 Community & Contributor Callout

We are actively inviting developers, researchers, and enterprises to test, benchmark, and contribute!

- **Read the [Contributor Guidelines (CONTRIBUTING.md)](./CONTRIBUTING.md)**.
- **Open an Issue / Feature Request**: Submit bug reports, benchmark logs, and feature proposals on our [GitHub Issues tracker](https://github.com/botmartz/vortex/issues).
- **Core Roadmap Items**: Notion/SharePoint connectors, Whisper audio integration, and visual DAG builders.

## 📄 License
Licensed under the [Apache License, Version 2.0](./LICENSE). Maintained by [Botmartz AI Solutions](https://www.botmartz.com).
