---
name: jev-late-chunking
description: Joint Embedding & Late Chunking (JEV) over full-document token windows with hierarchical parent residual blending.
---
# Botmartz VORTEX JEV Late-Chunking Skill
- Embed document context and AST node spans while blending parent section and global document vectors (`alpha * span + (1 - alpha) * parent_blend`).
- Track `doc_char_span`, `doc_token_span`, `parent_blend_alpha`, and `global_coherence_score`.
