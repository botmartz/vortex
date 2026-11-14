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
  <a href="#the-botmartz-open-source-ecosystem">The Botmartz Ecosystem</a> •
  <a href="#architectural-highlights">Architectural Highlights</a> •
  <a href="#side-by-side-benchmarking">Benchmarking With RAGFlow</a> •
  <a href="#docker--kubernetes">Docker & Kubernetes</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## What is Botmartz VORTEX?

**Botmartz VORTEX** is an open-source, enterprise-grade Omni-RAG and Deep Agent Harness engine built for developers who need **high retrieval fidelity**, **cryptographic update efficiency**, and **deterministic mathematical precision** without the heavy operational overhead of multi-container microservice stacks.

Whether you run on a lightweight developer laptop or scale into enterprise Kubernetes clusters, VORTEX runs in a **compact single process (<500 MB idle memory)** that natively embeds Rust tokenization, LanceDB vector storage, DuckDB 2.0 analytical processing, and an SQLite WAL state machine.

<p align="center">
  <img src="./docs/assets/vortex-ui-preview.png" alt="Botmartz VORTEX Studio UI Preview" width="100%" style="border-radius: 8px; border: 1px solid #E5E2DC;" />
</p>

---

## ⚡ Architectural Highlights

1. **Compact Single-Process Runtime**: Designed for zero ops sprawl. Boots in seconds locally without requiring external database containers or distributed orchestrators.
2. **$O(\Delta)$ BLAKE3 Merkle AST Diffing**: When documents or legal contracts update, VORTEX computes a Merkle diff over the document's Abstract Syntax Tree. Only modified subtrees are re-indexed, saving significant compute and embedding API costs.
3. **Deterministic Math (DuckDB KAG)**: Questions requiring calculations, aggregations, or spreadsheet data compile directly into in-memory DuckDB OLAP SQL queries for mathematically verified answers.
4. **Hierarchical Document Trees (H-RAG & JEV)**: Retains parent-child document hierarchy and applies late-chunking embeddings across full-document attention matrices before chunk pooling to eliminate context clipping.
5. **SmithDB & Pregel BSP Agent Harness**: Features a 4-superstep state machine with immutable checkpointing, waterfall span traces, and time-travel replay.
6. **Provider Agnostic**: Configurable for **Google Gemini (Primary)**, local **Ollama** (`gpt-oss:120b`, Llama 3), **llama.cpp server**, or **OpenAI/vLLM/SGLang**.

---

## 🌐 The Botmartz Open-Source Ecosystem

VORTEX operates alongside our specialized companion repositories:

| Repository | Focus & Role |
| :--- | :--- |
| **[botmartz/vortex](https://github.com/botmartz/vortex)** | **Core Engine**: Zero-sprawl Omni-RAG, H-RAG AST, DuckDB SQL, and React 19 Studio. |
| **[botmartz/llamaparse-pgvector-pipeline](https://github.com/botmartz/llamaparse-pgvector-pipeline)** | **Specialized Ingestion**: Vision-based AST layout & table extraction for complex PDFs and SEC 10-K balance sheets into PostgreSQL. |
| **[botmartz/mcp-postgres-wal-server](https://github.com/botmartz/mcp-postgres-wal-server)** | **Enterprise State Server**: MCP protocol server for PostgreSQL WAL checkpoints and Saga rollback transactions for distributed teams. |

---

## 🚀 Quickstart

### 1. Clone & Configure
```bash
git clone https://github.com/botmartz/vortex.git
cd vortex

# Copy the environment template
cp .env.example .env
```
*(Open `.env` and configure your preferred model provider, such as your Gemini or OpenAI API key, or leave blank to use local Ollama / llama.cpp).*

### 2. Python Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Build the React 19 Studio UI
```bash
cd web
bun install && bun run build
cd ..
```

### 4. Launch the Engine
```bash
uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420
```
Open **`http://127.0.0.1:8420`** in your browser to access the **Editorial Light Studio**.

---

## 🔬 Side-by-Side Benchmarking: Test Both VORTEX & RAGFlow

We believe the best way for developers to evaluate retrieval architectures is through open, empirical testing. 

Infiniflow's **RAGFlow** is an impressive and widely adopted platform with strong deep document vision capabilities. In VORTEX Studio, we included a built-in **Live Duel & Benchmark Tab** where developers can run side-by-side queries across both architectural approaches:
- **Try RAGFlow**: Test how full-document re-indexing and deep vision parsing perform on your document set.
- **Try VORTEX**: Compare how $O(\Delta)$ Merkle diffing and in-memory DuckDB OLAP SQL handle the same workload.
- **Benchmark Metrics**: Inspect latency, memory footprint, and numerical query precision on your own hardware.

---

## 🐳 Docker & Kubernetes

### Single Container Run
```bash
docker compose up -d
```
Or run directly:
```bash
docker run -d \
  --name botmartz-vortex \
  -p 8420:8420 \
  -v vortex_data:/app/data \
  --env-file .env \
  botmartz/vortex:latest
```

---

## 🤝 Community Feedback & Contributing

We warmly invite the AI and RAG community to test VORTEX on diverse enterprise corpora, challenge our benchmarks, and share your feedback!

- Read our **[Contributor Guidelines (CONTRIBUTING.md)](./CONTRIBUTING.md)**.
- Report observations, ask questions, or propose RFCs via **[GitHub Issues](https://github.com/botmartz/vortex/issues)**.
- High-priority community roadmap:
  - Connectors: Notion, SharePoint, Google Drive, and Confluence.
  - Multimodal: Native Whisper/WhisperX audio alignment into AST nodes.
  - UI: Interactive drag-and-drop workflow DAG builder.

## 📄 License
Licensed under the [Apache License, Version 2.0](./LICENSE). Maintained by [Botmartz AI Solutions](https://www.botmartz.com).
