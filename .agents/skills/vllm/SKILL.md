---
name: vllm
description: Distributed vLLM inference serving with PagedAttention, Automatic Prefix Caching (APC), AWQ/FP8 quantization, and OpenAI-compatible routing.
---
# Botmartz VORTEX vLLM Serving Skill
- Align `CAGPrefixBlock` ordering (`system -> corpus_skeleton -> pinned_ast_subtree -> session_memory`) for high APC KV-cache hit rates.
- Support local `llama.cpp`, Ollama, OpenAI, and vLLM clusters seamlessly.
