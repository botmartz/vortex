# Botmartz VORTEX: Technical Architecture & Tester's Field Guide

**Document Version:** 1.0.0  
**Target Audience:** Technical Leads, AI/ML Engineers, Product Architects, and Beta Evaluators  
**Repository:** [github.com/botmartz/vortex](https://github.com/botmartz/vortex)  
**License:** Apache 2.0  

---

## Part 1: In Plain English — Why Does VORTEX Exist?

If you have ever tried building or hosting a production RAG system (using tools like RAGFlow, Dify, or complex LangChain setups), you have likely run into three major roadblocks:

1. **The Infrastructure Nightmare:**  
   Most systems require 7 to 14 separate Docker containers just to test a single query (Elasticsearch, Redis, MinIO, MySQL, Celery workers). If you run them on a laptop, your computer slows to a crawl (8–16 GB of RAM taken up while idle).  
   *What VORTEX does:* It runs as a **single lightweight process (< 500 MB RAM idle)**. You can spin it up on your laptop or in a single tiny container in seconds.

2. **The Math & Spreadsheet Hallucination Problem:**  
   Standard RAG turns spreadsheets, invoices, and financial tables into plain text chunks. When an executive asks: *"What was our total revenue in Q3 across all European branches?"*, the AI tries to do mental math on noisy text and frequently hallucinates numbers.  
   *What VORTEX does:* It detects tables and loads them into **DuckDB** (an ultra-fast in-memory analytical SQL database). The AI generates an exact SQL query, calculates the math deterministically, and gives you a 100% accurate number with zero guesswork.

3. **The Document Update (Mutation) Waste:**  
   If you have a 300-page policy manual and change 2 sentences on page 140, existing engines re-read and re-embed all 300 pages from scratch ($O(N)$). If you have thousands of documents, your embedding API bills and compute hours explode.  
   *What VORTEX does:* It uses **cryptographic BLAKE3 Merkle trees** to map your documents. When a document changes, VORTEX diffs the tree and **only re-indexes the specific paragraph that changed**, skipping up to 90% of the re-indexing work.

4. **Context Blindness (Late Chunking):**  
   Standard tools blindly cut documents into 500-word blocks. If a crucial definition is in paragraph 1 and referenced in paragraph 5, cutting them apart means the AI misses the connection. VORTEX embeds the entire document first and slices it *afterwards* (**Late Chunking / JEV**), so every chunk retains full awareness of the whole document.

---

## Part 2: Quick Message You Can Send to Your Friends

Copy and send this directly to your friends, colleagues, or developer groups:

```text
Hey! We just open-sourced our in-house AI engine at Botmartz, called VORTEX, and I’d love for you to test it out and give me your honest feedback.

In short: it’s an Omni-RAG engine that replaces heavy 14-container setups (like RAGFlow and Dify) with a single process that uses under 500MB of RAM.

Why you'll find it interesting:
- Zero math hallucinations: It has an embedded DuckDB SQL engine inside it. When you query tables or financial sheets, it runs actual SQL queries instead of letting the LLM guess the math.
- Smart document updates: If you edit 2 sentences in a 50-page document, it uses cryptographic Merkle diffing to only re-index what changed (skipping 90% of re-embedding compute).
- Late Chunking (JEV): Chunks don't lose context because it looks at the full document attention before splitting.
- Built-in Studio: Has a clean editorial UI with a side-by-side benchmark tab where you can test questions across both architectures.
- Works with Gemini first, or local Ollama / llama.cpp models if you want to run offline.

How to run it (takes 2 minutes):
1. git clone https://github.com/botmartz/vortex.git && cd vortex
2. cp .env.example .env (paste your Gemini/OpenAI key or leave blank for local Ollama)
3. python3 -m venv .venv && source .venv/bin/activate && pip install -e .
4. cd web && bun install && bun run build && cd ..
5. uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420

Open http://127.0.0.1:8420 and drop some complex PDFs or spreadsheets in. Let me know what breaks, how the answers feel, and what you think of the speed!

Repo: https://github.com/botmartz/vortex
```

---

## Part 3: Deep Technical Architecture Specification

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT / INTERFACE TIER                         │
│   React 19 Studio (Alabaster Theme)  │  A2A Agent Mesh  │  MCP Gateway │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON-RPC (Port 8420)
┌───────────────────────────────────▼────────────────────────────────────┐
│                  FASTAPI CONTROL PLANE & INFERENCE ROUTER              │
│   • Multi-Provider Cascade: Gemini 2.5 Flash ──> Ollama ──> llama.cpp  │
│   • Entropy-Adaptive Router (EAR): Shannon H(q) Fusion Tuning          │
│   • Sentinel Claim Judge (SCG): Atomic Grounding & Abstention Gates    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
     Retrieved Tree │                 SQL Aggregates │
                    │                                │
┌───────────────────▼──────────────────┐ ┌───────────▼──────────────────┐
│      H-RAG & MERKLE AST ENGINE       │ │       KAG DUCKDB 2.0 OLAP     │
│  • AST Node Structural Parser        │ │  • In-Memory Columnar Tables  │
│  • BLAKE3 Subtree Merkle Hashing     │ │  • Deterministic Math & Aggr  │
│  • O(Δ) Mutation Diffing (~88% skip) │ │  • Self-Healing Fallback SQL  │
│  • JEV (Late Chunking) Attention     │ │  • Zero Hallucination Arithmetic
└───────────────────┬──────────────────┘ └───────────┬──────────────────┘
                    │                                │
                    └────────────────┬───────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                    EMBEDDED ZERO-SPRAWL STORAGE                        │
│   LanceDB (Vector / HNSW)  │  Tantivy (BM25)  │  SmithDB (SQLite WAL) │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. H-RAG AST & Cryptographic Merkle Diffing
- **AST Generation**: Instead of splitting raw text by character counts (`\n\n` or 500 tokens), documents are parsed into Abstract Syntax Trees capturing headings, sub-clauses, lists, and tabular tensors.
- **BLAKE3 Content Addressing**: Every AST node carries a 32-byte cryptographic hash computed from its normalized content and its children's hashes.
- **Delta-Only Ingestion**: When updating document $D \to D'$, the engine traverses the tree. Subtrees with matching Merkle roots are skipped entirely. Only mutated nodes and their direct ancestors are re-vectorized.

#### 2. JEV (Late Chunking)
- Standard chunking passes disjoint segments into an embedding model:
  $$\mathbf{e}_i = \text{Pool}(\text{Transformer}(c_i))$$
- VORTEX Late Chunking passes the full continuous document sequence through the transformer encoder and extracts chunk embeddings from the boundary token slices of the complete sequence hidden states:
  $$\mathbf{H} = \text{Transformer}(d_{1:N}), \quad \mathbf{e}_i = \text{MeanPool}(\mathbf{H}[\text{start}_i:\text{end}_i])$$
- Each chunk preserves full cross-document contextual self-attention.

#### 3. KAG (Knowledge-Augmented Generation) & Embedded DuckDB 2.0
- Documents with structured rows or synced databases (SQLite, CSV, JSON) are registered into embedded **DuckDB OLAP** tables.
- The query router assesses whether a question requires arithmetic, aggregation, or filtering.
- Queries generate deterministic SQL:
  ```sql
  SELECT kyc_tier, COUNT(*) AS volume, SUM(amount_usd) AS settled_volume
  FROM settled_remittances
  WHERE status = 'SETTLED'
  GROUP BY kyc_tier;
  ```
- The execution output is fed to the synthesizer as verified ground truth, eliminating numerical hallucination.

#### 4. SmithDB & 4-Superstep Pregel BSP Agent Harness
- Autonomous multi-agent coordination is executed via Bulk Synchronous Parallel (BSP) supersteps:
  1. `supervisor_eval`: Evaluates intent and routes to sub-specialists.
  2. `retriever_dispatch`: Concurrently executes BM25, JEV vector search, and KAG SQL.
  3. `verifier_gate`: The Self-Correcting Claim Judge (SCG) audits claims against retrieved AST node citations.
  4. `output_finalize`: Formats the verified synthesis or invokes hard abstention if groundedness falls below threshold.
- All state transitions and checkpoints are recorded in `vortex_smithdb.sqlite3` with WAL mode enabled, supporting time-travel execution replay.

---

## Part 4: 5-Minute Evaluator Checklist for Friends

When sending this to evaluators, ask them to test these 3 concrete scenarios:

- [ ] **Scenario A: The Math & Table Test**  
  Upload a small CSV or paste a table with numbers. Ask: *"What is the total sum and average of [column]?"* Check if VORTEX executes DuckDB SQL and outputs the exact number without hallucination.
- [ ] **Scenario B: The Document Edit Test**  
  Upload a Markdown file or PDF. Make a small edit in one section and re-upload with version 2. Check the telemetry to see the Merkle diff skip unchanged nodes.
- [ ] **Scenario C: The Live Duel Benchmark**  
  Click the **RAGFlow Live Duel** tab in the UI (`http://127.0.0.1:8420`), run the benchmark query, and review the side-by-side latency, memory footprint, and citation telemetry.
