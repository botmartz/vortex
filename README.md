<p align="center">
  <img src="./docs/assets/vortex-logo.svg" width="140" height="140" alt="Botmartz VORTEX Logo" />
</p>

<h1 align="center">Botmartz VORTEX</h1>

<p align="center">
  <b>Frontier Omni-RAG Engine with Native VeriFAI™ Grounding & Verification</b><br>
  <i>Sub-500MB Zero-Sprawl Runtime · VeriFAI™ Zero-Hallucination Gate · H-RAG AST Trees · JEV Late Chunking · BLAKE3 Merkle Diffing · KAG DuckDB OLAP SQL · SmithDB</i>
</p>

<p align="center">
  <a href="https://github.com/botmartz/vortex/stargazers"><img src="https://img.shields.io/github/stars/botmartz/vortex?style=flat-square&color=B85D3B" alt="GitHub Stars" /></a>
  <a href="https://github.com/botmartz/vortex/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/Release-v1.0.0-B85D3B?style=flat-square" alt="Release v1.0.0" /></a>
  <a href="https://github.com/botmartz/vortex/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-141413?style=flat-square" alt="License" /></a>
  <a href="https://hub.docker.com/r/botmartz/vortex"><img src="https://img.shields.io/badge/Docker-Single%20Container-2A6F4E?style=flat-square" alt="Docker" /></a>
  <a href="https://github.com/botmartz/vortex/issues"><img src="https://img.shields.io/github/issues/botmartz/vortex?style=flat-square&color=B85D3B" alt="Open Issues" /></a>
</p>

<p align="center">
  <a href="#what-is-botmartz-vortex">Overview</a> •
  <a href="#architectural-highlights">Architecture</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#python-sdk-usage">Python SDK</a> •
  <a href="#the-botmartz-open-source-ecosystem">Ecosystem</a> •
  <a href="#side-by-side-benchmarking">Benchmarking</a> •
  <a href="#open-core-commercial-model">Open Core Model</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## What is Botmartz VORTEX?

**Botmartz VORTEX** is an open-source, enterprise-grade Omni-RAG and Deep Agent Harness engine with **native VeriFAI™ Grounding & Verification**. Built for mission-critical deployments where hallucinations are not an option, VORTEX combines:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   BOTMARTZ VORTEX (Combined Engine)                    │
├───────────────────────────────────┬────────────────────────────────────┤
│ 1. VORTEX RUNTIME (The Muscle)    │ 2. VeriFAI™ GROUND (The Referee)   │
│ • Sub-500MB Rust/Python daemon    │ • Atomic claim extraction          │
│ • LanceDB vector indexing         │ • SHA-256 chunk cryptographic hash │
│ • DuckDB OLAP SQL for exact math  │ • Cross-attention citation matcher │
│ • BLAKE3 Merkle AST diffing       │ • Deterministic abstention gate    │
│   (Fast Retrieval & Ingestion)    │   (Zero-Hallucination Proof)       │
└───────────────────────────────────┴────────────────────────────────────┘
```

1. **VORTEX Runtime (The Muscle)**: A compact single-process engine running under 500 MB RAM that unifies Rust tokenization, LanceDB vector storage, DuckDB 2.0 analytical processing, and an SQLite WAL state machine.
2. **VeriFAI™ Ground (The Referee)**: An automated zero-hallucination verification layer that audits synthesized answers into atomic claims, checks SHA-256 chunk cryptographic hashes, matches cross-attention citations, and enforces deterministic evidence-grounded abstention.

<p align="center">
  <img src="./docs/assets/vortex-ui-preview.png" alt="Botmartz VORTEX Studio UI Preview with VeriFAI Grounding" width="100%" style="border-radius: 8px; border: 1px solid #E5E2DC;" />
</p>

---

## ⚡ Architectural Highlights

1. **Native VeriFAI™ Grounding Referee**: Verifies every synthesized sentence against cryptographic chunk hashes and analytical SQL rows, calculating atomic claim verification scores and enforcing strict abstention gates when evidence is missing.
2. **Compact Single-Process Runtime**: Designed for zero ops sprawl. Boots in seconds locally without requiring external database containers or distributed orchestrators.
3. **$O(\Delta)$ BLAKE3 Merkle AST Diffing**: When documents or legal contracts update, VORTEX computes a Merkle diff over the document's Abstract Syntax Tree. Content-addressed node IDs ensure that newly inserted paragraphs only re-embed modified subtrees, saving ~90% of re-indexing compute.
4. **Deterministic Math (DuckDB 2.0 KAG)**: Questions requiring calculations, aggregations, or spreadsheet data compile directly into in-memory DuckDB OLAP SQL queries for mathematically verified answers without LLM hallucinations.
5. **Hierarchical Document Trees (H-RAG & JEV)**: Retains parent-child document hierarchy and applies late-chunking embeddings across full-document attention matrices before chunk pooling to eliminate context clipping.
6. **SmithDB & Pregel BSP Agent Harness**: Features a 4-superstep state machine with immutable checkpointing, waterfall span traces, and time-travel replay over SQLite WAL (PostgreSQL schema compatible).
7. **Local Multi-Format File Ingestion**: Drag-and-drop CSV, PDF, Markdown, and text files directly in the UI. CSV datasets are compiled into DuckDB tables for instant analytical querying.
8. **Provider Agnostic**: Configurable for **Google Gemini (Primary)**, local **Ollama** (`gpt-oss:120b`, Llama 3), **llama.cpp server**, or **OpenAI/vLLM/SGLang**.

---

## 💻 Python SDK Usage

Install and import VORTEX directly into your Python applications with native VeriFAI verification:

```python
import botmartz_engine as vortex

# 1. Initialize Engine & Ingest Documents or CSV Datasets
engine = vortex.BotmartzDelegationGraph()
engine.ingest_markdown(
    doc_id="cf34_engine_manual",
    uri="vault://specs/cf34_manual.md",
    markdown_text="# Chapter 72: Turbine Inspection Intervals\nInspection required every 1,500 flight hours."
)

# 2. Query with Native VeriFAI Grounding
res = engine.query("What are the inspection intervals for turbine blades?")

# 3. Inspect VeriFAI Attribution
audit = vortex.VeriFAIEngine.audit(
    answer=res["result"]["answer"],
    evidence_hits=res["result"]["hrag_jev_hits"],
    sql_rows=res["result"]["kag_sql_rows"],
    sql_query=res["result"]["kag_sql_executed"]
)

print("Answer:", audit.text)
print("VeriFAI Confidence:", f"{round(audit.verifai_confidence * 100, 1)}%")
print("Verdict:", audit.verdict.value)  # VERIFIED_GROUNDED
for claim in audit.claims:
    print(f"  • [{claim.verdict.value}] {claim.statement}")
    for cit in claim.citations:
        print(f"      Citation: {cit.source_id} | SHA-256: {cit.sha256_hash[:12]}")
```

---

## 🚀 Quickstart

### 1. Clone & Configure
```bash
git clone https://github.com/botmartz/vortex.git
cd vortex

# Copy the environment template
cp .env.example .env
```
*(Open `.env` and configure your preferred model provider, such as your Gemini or OpenAI API key, or leave blank to use local Ollama / llama.cpp).*

### 2. Python Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Build the Studio UI
```bash
cd web
bun install && bun run build
cd ..
```

### 4. Launch the Engine
```bash
uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420
```
Open **`http://127.0.0.1:8420`** in your browser to access the **VORTEX Studio** with the persistent sidebar, digital adoption walkthrough, and VeriFAI audit views.

---

## 🌐 The Botmartz Open-Source Ecosystem

VORTEX operates alongside our specialized companion repositories:

| Repository | Focus & Role |
| :--- | :--- |
| **[botmartz/vortex](https://github.com/botmartz/vortex)** | **Core Engine**: Zero-sprawl Omni-RAG, VeriFAI™ Grounding, H-RAG AST, DuckDB SQL, and Studio UI. |
| **[botmartz/llamaparse-pgvector-pipeline](https://github.com/botmartz/llamaparse-pgvector-pipeline)** | **Specialized Ingestion**: Vision-based AST layout & table extraction for complex PDFs and SEC 10-K balance sheets into PostgreSQL. |
| **[botmartz/mcp-postgres-wal-server](https://github.com/botmartz/mcp-postgres-wal-server)** | **Enterprise State Server**: MCP protocol server for PostgreSQL WAL checkpoints and Saga rollback transactions for distributed teams. |

---

## 🔬 Side-by-Side Benchmarking: VORTEX vs. Traditional Multi-Container RAG

We believe the best way for developers to evaluate retrieval architectures is through open, empirical testing on real hardware.

In VORTEX Studio, we included a built-in **Live Architecture Benchmark Tab** where developers can run side-by-side queries across both architectural approaches:
- **Traditional Multi-Container Baseline**: Test how conventional multi-container flat-chunking and text approximation handle technical queries.
- **Botmartz VORTEX**: Compare how $O(\Delta)$ Merkle diffing, native VeriFAI™ grounding, and in-memory DuckDB OLAP SQL handle the exact same workload.
- **Benchmark Metrics**: Inspect latency, memory footprint (<500MB vs 8–16GB), and numerical query precision on your own hardware.

---

## 🛡️ Open Core Commercial Model

Botmartz VORTEX follows a transparent, developer-first open core architecture:

| Tier | License | Target Audience | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **VORTEX Community** | **Apache 2.0 (Free)** | Developers, Startups, Research | Sub-500MB embedded runtime, H-RAG AST layout, JEV late chunking, DuckDB 2.0 KAG, BLAKE3 Merkle diffing, local CSV/file ingestion, and basic VeriFAI chunk citations. |
| **VORTEX Enterprise with VeriFAI™ Pro** | **Commercial** | Regulated Enterprises, MRO, Defense | Deep cross-encoder claim verification, automated regulatory audit ledgers, compliance signature gates, multi-tenant RBAC, and priority SLA (powers **AvioTron MRO OS**). |

---

## 🐳 Docker & Kubernetes

### Single Container Run
```bash
docker compose up -d
```
Or run directly:
```bash
docker run -d \
  --name botmartz-vortex \
  -p 8420:8420 \
  -v vortex_data:/app/data \
  --env-file .env \
  botmartz/vortex:latest
```

---

## 🤝 Community Feedback & Contributing

We warmly invite the AI and RAG community to test VORTEX on diverse enterprise corpora, challenge our benchmarks, and share your feedback!

- Read our **[Contributor Guidelines (CONTRIBUTING.md)](./CONTRIBUTING.md)**.
- Report observations, ask questions, or propose RFCs via **[GitHub Issues](https://github.com/botmartz/vortex/issues)**.
- High-priority community roadmap:
  - Connectors: Notion, SharePoint, Google Drive, and Confluence.
  - Multimodal: Native Whisper/WhisperX audio alignment into AST nodes.
  - UI: Interactive drag-and-drop workflow DAG builder.

## 📄 License
Licensed under the [Apache License, Version 2.0](./LICENSE). Maintained by [Botmartz AI Solutions](https://www.botmartz.com).
