---
title: 03 — CAG (Radix KV-Cache) & KAG (DuckDB Deterministic SQL) Engine
tags:
  - botmartz
  - spec
  - cag
  - kag
  - duckdb
  - vllm
created: 2026-11-14
owner: botmartz-inference
---

# 03 — CAG (Radix KV-Cache) & KAG (DuckDB Deterministic SQL) Engine

## 1. Cache-Augmented Generation (CAG)
- **RadixAttention Prefix Tree**: Coordinates with vLLM / SGLang (and local `llama.cpp` prompt cache slots) by sorting context blocks deterministically:
  `[System Prompt] -> [Pinned Corpus Skeleton / H-RAG Root Summaries] -> [Hot Subtree Context] -> [Dynamic Query & Delta Chunks]`
- **Deterministic Prefix Hashing**: Every CAG block is keyed by its BLAKE3 Merkle hash so unchanged document subtrees never invalidate downstream KV blocks unless modified.

## 2. Knowledge-Augmented Generation (KAG) via Embedded DuckDB
- **Deterministic Tabular Mapper**: Every `ASTNode` of type `Table` or structured JSON/CSV payload is automatically normalized into a strongly-typed DuckDB table (`DuckDBTableSchema`) linked back to `doc_id` and `ast_node_id`.
- **Zero-Hallucination Analytical Execution**: Quantitative, aggregation, filtering, and join queries are routed by the `InferenceRouter` to DuckDB SQL execution rather than approximate vector similarity.
