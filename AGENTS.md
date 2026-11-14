# Botmartz Omni-RAG & Autonomous Generation Engine (`AGENTS.md`)

You are operating inside the **Botmartz Omni-RAG & Autonomous Generation Engine** repository.

## Core Architectural Pillars
1. **H-RAG (Hierarchical Document Trees)**: AST-based structural parsing and parent-child-sibling tree traversal instead of flat lossy chunks.
2. **JEV (Joint Embedding & Late Chunking)**: Full-document / long-window token embeddings computed prior to chunk pooling to preserve global cross-chunk context.
3. **CAG (Cache-Augmented Generation)**: Deterministic prefix ordering and RadixAttention KV-cache residency via vLLM / SGLang / llama.cpp.
4. **KAG (Knowledge-Augmented Generation)**: Embedded DuckDB/SQLite deterministic SQL execution over extracted tabular schemas and entity graphs.
5. **Cryptographic Document Versioning**: BLAKE3 Merkle tree content-addressable chunk diffing for surgical incremental re-indexing on document mutations.
6. **Zero-Sprawl Runtime**: Embedded Rust core daemon (`botmartz-core`, `botmartz-ast`, `botmartz-storage`, `botmartz-mcp`) paired with LanceDB + Tantivy + DuckDB and a Python FastAPI/LangGraph orchestration layer.
7. **Native MCP Server**: First-class Model Context Protocol server exposing H-RAG, JEV, KAG, and CAG tools to IDEs and autonomous agents.

## Core Subagents
- `botmartz-architect`: Lead Systems & Rust/Inference Orchestrator
- `botmartz-parser`: Document AST, Vision & Late-Chunking (`H-RAG` + `JEV` + Merkle Diffing)
- `botmartz-inference`: CAG, Radix KV-Cache & Router (`vLLM`/`SGLang` + `DuckDB KAG` + Evaluation Sentinel)
- `botmartz-obsidian`: Obsidian Vault & Technical RFCs (`docs/obsidian-vault`)
