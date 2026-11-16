---
name: sentinel-abstention
description: Botmartz Evidence-Grounded Abstention Sentinel verifying Merkle provenance chains and blocking ungrounded hallucinations.
---
# Botmartz VORTEX Evaluation Sentinel Skill
- Verify every generated response against retrieved Merkle-hashed AST spans and DuckDB SQL result rows.
- Trigger `abstained=True` with explicit gap reporting whenever grounded evidence falls below threshold.
