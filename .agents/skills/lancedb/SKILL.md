---
name: lancedb
description: Embedded Arrow-native LanceDB multi-vector storage for JEV Late-Chunking spans and AST node pointers.
---
# Botmartz VORTEX LanceDB Vector Engine Skill
- Store normalized JEV embeddings, `doc_id`, `ast_node_id`, `merkle_hash`, and span boundaries in LanceDB tables under `data/lancedb`.
- Fuse dense JEV vector ranks with BM25 lexical ranks via RRF.
