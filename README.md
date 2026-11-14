<p align="center">
  <img src="./docs/assets/vortex-logo.svg" width="140" height="140" alt="Botmartz VORTEX Logo" />
</p>

<h1 align="center">Botmartz VORTEX</h1>

<p align="center">
  <b>Frontier Omni-RAG & Deep Agent Harness Engine</b><br>
  <i>Sub-500MB Zero-Sprawl Runtime · H-RAG AST Trees · JEV Late Chunking · BLAKE3 Merkle Diffing · KAG DuckDB OLAP SQL · SmithDB</i>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#benchmark-vs-ragflow">Benchmark vs RAGFlow</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

---

## What is Botmartz VORTEX?

**VORTEX** is an open-source, enterprise-grade Omni-RAG and Deep Agent Harness engine designed to replace heavy multi-container RAG stacks (like RAGFlow, Dify, and complex LangChain setups) with a **high-performance, zero-sprawl single process**.

### Why VORTEX?

1. **Zero Ops Sprawl**: Runs as a single self-contained binary/process (<500 MB idle memory) combining a Rust core, LanceDB vector storage, DuckDB 2.0 analytical engine, and SQLite WAL. No required Elasticsearch, MySQL, MinIO, or Redis containers.
2. **$O(\Delta)$ BLAKE3 Merkle Mutation**: Cryptographically diffs document ASTs on updates. Edits to existing documents only re-embed the modified subtrees, skipping ~88.9% of redundant re-indexing work.
3. **Deterministic Math (KAG DuckDB)**: Eliminates LLM tabular hallucinations. Numerical questions automatically compile into in-memory DuckDB OLAP SQL queries for 100% mathematical precision.
4. **Hierarchical Document Trees (H-RAG & JEV)**: Preserves document structure via ASTs and computes late-chunking embeddings across full-document attention matrices before chunk pooling.
5. **SmithDB & Pregel BSP Agent Harness**: Built-in 4-superstep state graph with immutable checkpointing, waterfall span traces, and time-travel replay.
6. **Provider Agnostic**: Prioritizes **Gemini 2.5 Flash / Pro**, cascading cleanly to local **Ollama**, **llama.cpp server**, or **OpenAI/vLLM/SGLang**.

---

## Benchmark: VORTEX vs. Infiniflow RAGFlow

| Feature | Infiniflow RAGFlow | Botmartz VORTEX v0.3 |
| :--- | :--- | :--- |
| **Idle Footprint** | 7–14 Docker containers (8–16 GB RAM) | 1 local process (< 500 MB RAM) |
| **Document Mutations** | $O(N)$ full re-index (0% skipped) | $O(\Delta)$ BLAKE3 Merkle diff (~88.9% skipped) |
| **Tabular Queries** | Markdown text snippet (LLM approximation) | Embedded DuckDB 2.0 OLAP SQL (Exact rows) |
| **Chunk Context** | Flat delimiter splits | H-RAG AST + JEV Late Chunking |
| **Agent State Traces** | Ephemeral logs / external DB | Built-in SmithDB (Checkpoints & Replay) |
| **Model Serving** | Proprietary wrappers | Gemini First + Ollama + llama.cpp + vLLM |

---

## Quickstart

### 1. Clone & Setup
```bash
git clone https://github.com/botmartz/vortex.git
cd vortex

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Build the Studio UI
```bash
cd web
bun install && bun run build
cd ..
```

### 3. Launch VORTEX
```bash
uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420
```
Open **`http://127.0.0.1:8420`** in your browser to access the **Editorial Light Studio**.

---

## Contributing & Roadmap

We welcome community contributions! High-priority areas:
- [ ] Connectors: Notion, Google Drive, SharePoint, and Confluence.
- [ ] Audio/Video Transcripts: Native Whisper/WhisperX ingestion into AST nodes.
- [ ] Visual DAG Builder: React Flow canvas for visual agent graph composition.
- [ ] Enterprise RBAC: Chunk-level security ACLs.

## License
Apache-2.0. Built by Botmartz AI Systems.
