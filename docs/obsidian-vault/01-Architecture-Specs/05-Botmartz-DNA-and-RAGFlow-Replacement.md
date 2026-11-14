---
title: 05 — Botmartz DNA & In-House RAGFlow Replacement Blueprint
tags:
  - botmartz
  - strategy
  - ragflow
  - vllm
  - sglang
  - cag
  - kag
created: 2026-11-14
owner: botmartz-architect
---

# 05 — Botmartz DNA & In-House RAGFlow Replacement Blueprint

## 1. Botmartz Enterprise DNA
- **Company**: Botmartz AI Solutions Private Limited (`botmartz.com`), founded by **Soham Sharma** (Founder & Principal AI Architect).
- **Core Doctrine**: Determinism over black-box randomness; Private VPC & air-gapped sovereignty; Evidence-Grounded Abstention; Stateful LangGraph + WAL state machines; Hybrid RRF retrieval.
- **Academy**: Forward Deployed AI Engineer (FDE) Foundry & intensive weekend production masterclasses.

## 2. Why We Replace `infiniflow/ragflow` In-House
1. **Zero-Sprawl Rust + Embedded Storage Triad**: Replaces RAGFlow's heavy 5-container stack (Elasticsearch/Infinity + MySQL + Redis + MinIO) with embedded **Rust (`Tantivy` + `BLAKE3 Merkle AST`) + `LanceDB` + `DuckDB`**.
2. **True JEV Late Chunking + H-RAG**: Preserves global cross-chunk context across 8k–32k token windows before pooling along AST node spans.
3. **SGLang RadixAttention & vLLM Prefix Caching (CAG)**: Pins corpus skeletons and hot AST subtrees directly in GPU KV-cache.
4. **Deterministic KAG via DuckDB**: Routes tabular and quantitative queries to verified read-only SQL instead of lossy markdown table chunks.
5. **Evidence-Grounded Abstention Sentinel**: Enforces Botmartz's strict zero-hallucination abstention gate with cryptographic Merkle provenance.
