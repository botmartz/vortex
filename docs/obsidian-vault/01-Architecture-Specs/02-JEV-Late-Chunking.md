---
title: 02 — JEV (Joint Embedding & Late Chunking) Specification
tags:
  - botmartz
  - spec
  - jev
  - late-chunking
created: 2026-11-14
owner: botmartz-parser
---

# 02 — JEV (Joint Embedding & Late Chunking) Specification

## Problem Solved
Standard chunking embeds chunks in isolation (`Embed(Chunk_i)`), losing pronouns, document-level entities, and implicit context defined earlier in the document.

## JEV Pipeline
1. **Long-Context Forward Pass**:
   - Pass full documents or macro-sections (up to 8k–32k tokens) through the long-context embedding backbone to obtain contextualized token-level hidden states $H = [h_1, h_2, \dots, h_T] \in \mathbb{R}^{T \times d}$.
2. **AST-Aligned Late Span Pooling**:
   - Map each `ASTNode` character span $[c_{\text{start}}, c_{\text{end}})$ to token indices $[t_{\text{start}}, t_{\text{end}})$.
   - Pool token embeddings within each AST node boundary (mean pooling + hierarchical parent residual blending):
     $$v_{\text{node}} = \text{Normalize}\left(\alpha \cdot \frac{1}{t_{\text{end}} - t_{\text{start}}} \sum_{t=t_{\text{start}}}^{t_{\text{end}}-1} h_t + (1 - \alpha) \cdot v_{\text{parent}}\right)$$
3. **LanceDB Multi-Vector Storage**:
   - Persist `JEVChunkMetadata` alongside the contextualized vector, parent vector pointer, and token span boundaries in LanceDB.
