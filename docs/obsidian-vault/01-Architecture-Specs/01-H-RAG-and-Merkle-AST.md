---
title: 01 — H-RAG Hierarchical Document Trees & BLAKE3 Merkle Versioning
tags:
  - botmartz
  - spec
  - h-rag
  - merkle
created: 2026-11-14
owner: botmartz-parser
---

# 01 — H-RAG Hierarchical Document Trees & BLAKE3 Merkle Versioning

## Problem Solved
Traditional RAG pipelines slice documents into flat, fixed-window chunks, destroying section hierarchy, table headers, and cross-section relationships. Furthermore, mutating a single paragraph in a 500-page manual forces legacy engines to re-embed the entire document.

## Architecture
1. **Abstract Document Tree (`DocumentAST`)**:
   - Every document is parsed into a typed tree of `ASTNode` elements (`Document`, `Section`, `Subsection`, `Paragraph`, `Table`, `CodeBlock`, `Equation`, `Figure`).
   - Each node tracks `parent_id`, `children_ids`, `prev_sibling_id`, `next_sibling_id`, `depth`, and `structural_path` (e.g., `["Section 4", "4.2 Thermal Limits", "Table 4.1"]`).
2. **Cryptographic Merkle Versioning (`MerkleDiffEngine`)**:
   - Leaf nodes compute `content_hash = BLAKE3(normalized_text || node_type || metadata)`.
   - Interior nodes compute `merkle_hash = BLAKE3(content_hash || child_1.merkle_hash || ... || child_n.merkle_hash)`.
   - On document update, `diff_trees(old_tree, new_tree)` traverses top-down in $O(k \log N)$ time, skipping any subtree whose `merkle_hash` is unchanged and emitting surgical `Added`, `Modified`, and `Deleted` node deltas.
