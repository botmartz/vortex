---
name: sglang
description: SGLang RadixAttention KV-cache tree reuse and xgrammar constrained structured generation for deterministic Botmartz agents.
---
# Botmartz VORTEX SGLang RadixAttention Skill
- Pass `cache_salt` keyed by root BLAKE3 Merkle hashes to preserve RadixAttention tree reuse across multi-turn queries.
- Use constrained JSON decoding for deterministic NL-to-SQL and A2A agent handoffs.
