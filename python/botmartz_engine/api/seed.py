"""Default enterprise knowledge seed for Botmartz VORTEX Engine."""

from __future__ import annotations

from ..agents import BotmartzDelegationGraph


BOTMARTZ_CLUSTER_SPEC = """# Botmartz VORTEX Enterprise Cluster & Architecture Specification
Botmartz AI Solutions Private Limited (founded by Soham Sharma) builds deterministic, air-gapped and Private VPC AI infrastructure.

## 1. Core Architectural Pillars
Botmartz VORTEX replaces legacy 6-container RAG deployments with a Zero-Sprawl Rust Core Daemon, LanceDB multi-vector storage, Okapi BM25 lexical scoring, Embedded DuckDB KAG SQL, and SGLang/vLLM RadixAttention CAG prefix caching.

## 2. Sovereign Workstation & Cluster Hardware Telemetry
| node_id | cpu_architecture | system_ram_gb | gpu_vram_gb | storage_tb | kv_cache_hit_pct |
| --- | --- | --- | --- | --- | --- |
| vortex-beast-01 | AMD Threadripper | 128 | 16 | 8 | 94.5 |
| vortex-cluster-02 | Dual EPYC 9654 | 512 | 80 | 32 | 97.2 |
| vortex-edge-03 | Ryzen AI Max | 64 | 24 | 4 | 91.8 |

## 3. Evidence-Grounded Abstention Policy
Whenever retrieved H-RAG AST spans or DuckDB KAG SQL rows lack sufficient entailment confidence, the Evaluation Sentinel enforces ABSTAINED_INSUFFICIENT_EVIDENCE rather than fabricating answers.
"""


TRADITIONAL_RAG_VS_VORTEX_SPEC = """# Multi-Container Traditional RAG vs Botmartz VORTEX Architectural Benchmark
Botmartz VORTEX was engineered to eliminate multi-container sprawl, chunk context blindness, and full-file re-indexing overhead found in traditional legacy RAG pipelines.

## 1. Benchmark Comparison Matrix
| engine_name | runtime_containers | idle_ram_footprint | chunking_method | mutation_diff_complexity | tabular_kag_backend | kv_prefix_caching |
| --- | --- | --- | --- | --- | --- | --- |
| legacy_multi_container_rag | 14 | 8 to 16 GB RAM | Pre-Embedding Flat Chunking | Full Re-Index O(N) | LLM Text Approximation | None |
| botmartz_vortex | 1 | Under 500 MB | H-RAG AST + JEV Late Chunking | BLAKE3 Merkle O(k log N) | Embedded DuckDB OLAP SQL | SGLang RadixAttention CAG |

## 2. Production SLA & Latency Targets
Botmartz VORTEX achieves sub-50ms time-to-first-token (TTFT) on repeated enterprise corpora by pinning Merkle-hashed AST skeletons into RadixAttention KV-cache prefix blocks.
"""


def seed_default_corpus(engine_graph: BotmartzDelegationGraph) -> None:
    if not engine_graph.state.documents:
        engine_graph.ingest_markdown(
            doc_id="botmartz_architecture",
            uri="vault://specs/botmartz_architecture.md",
            markdown_text=BOTMARTZ_CLUSTER_SPEC,
            version=1,
        )
        engine_graph.ingest_markdown(
            doc_id="architecture_benchmark",
            uri="vault://benchmarks/traditional_vs_vortex.md",
            markdown_text=TRADITIONAL_RAG_VS_VORTEX_SPEC,
            version=1,
        )
