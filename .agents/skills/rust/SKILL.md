---
name: rust
description: Rust systems engineering for Botmartz Core Daemon, BLAKE3 Merkle AST trees, Tantivy BM25 search, RRF fusion, and zero-copy serialization.
---
# Botmartz VORTEX Rust Core Skill
- Use workspace crates: `botmartz-ast`, `botmartz-storage`, `botmartz-mcp`, `botmartz-core`.
- Implement bottom-up BLAKE3 Merkle tree hashing and top-down $O(k \log N)$ surgical diffing.
- Implement deterministic BM25 lexical scoring and Reciprocal Rank Fusion (RRF).
- Keep zero compiler warnings (`cargo test` clean).
