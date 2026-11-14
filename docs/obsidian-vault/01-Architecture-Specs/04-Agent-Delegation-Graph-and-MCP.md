---
title: 04 — Agent Delegation Graph & Native MCP Server
tags:
  - botmartz
  - spec
  - agents
  - langgraph
  - mcp
created: 2026-11-14
owner: botmartz-architect
---

# 04 — Agent Delegation Graph & Native MCP Server

## Runtime Delegation Pipeline
```mermaid
stateDiagram-v2
    [*] --> IngestionAgent: Document / Mutation Event
    IngestionAgent --> StorageIndexAgent: AST + Merkle Delta + JEV Spans
    StorageIndexAgent --> [*]: Indexed in LanceDB + Tantivy + DuckDB

    [*] --> InferenceRouter: User / MCP Query
    InferenceRouter --> StorageIndexAgent: Hybrid H-RAG + JEV + KAG Retrieval
    StorageIndexAgent --> InferenceRouter: Contextual AST Subtrees + SQL Rows + CAG Prefix
    InferenceRouter --> EvaluationSentinel: Synthesized Response + Citations
    EvaluationSentinel --> InferenceRouter: Retry / Refine (if groundedness < threshold)
    EvaluationSentinel --> [*]: Verified Response + Cryptographic Provenance
```

## Native MCP Tools Exposed
- `botmartz_ingest_document`: Parse document into H-RAG AST, compute BLAKE3 Merkle diff, extract tables into DuckDB, and store JEV vectors.
- `botmartz_hybrid_query`: Execute routed H-RAG + JEV + KAG + CAG query with Evaluation Sentinel verification.
- `botmartz_sql_query`: Execute deterministic read-only SQL against the embedded DuckDB KAG store.
- `botmartz_inspect_ast`: Inspect the hierarchical document tree and Merkle version history for any document.
