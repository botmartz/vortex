---
title: 07 — A2A & MCP Protocol Mesh
tags:
  - botmartz
  - spec
  - a2a
  - mcp
  - protocol
  - json-rpc
  - agents
created: 2026-11-14
owner: botmartz-architect
status: active
---

# 07 — A2A & MCP Protocol Mesh

> [!IMPORTANT]
> **Core Architectural Mission**: Enable seamless interoperability across IDEs, external autonomous agents, and internal specialist agents. Botmartz VORTEX exposes dual open protocols:
> 1. **Google / Linux Foundation Agent-to-Agent (A2A) Protocol**: Standardized `/.well-known/agent.json` discovery and `/a2a` JSON-RPC 2.0 multi-agent task execution.
> 2. **Anthropic Model Context Protocol (MCP)**: Native Streamable HTTP (`/mcp`) and stdio transport exposing VORTEX AST, KAG, CAG, and Merkle capabilities.

---

## 1. High-Level Protocol Architecture

```mermaid
flowchart TD
    subgraph Clients ["Autonomous Clients & Environments"]
        IDE["IDE / Cursor / Windsurf / Claude Desktop (MCP Stdio/HTTP)"]
        ExternalAgent["External Autonomous Agent Network (A2A Protocol)"]
        StudioUI["Botmartz VORTEX Studio (FastAPI REST & UI)"]
    end

    subgraph Gateway ["VORTEX Gateway & Protocol Mesh (FastAPI :8420)"]
        IDE -->|MCP Streamable HTTP / Stdio| MCPHandler["MCP Server (mcp_server.py)"]
        ExternalAgent -->|GET /.well-known/agent.json| AgentCard["A2A Agent Card Discovery"]
        ExternalAgent -->|POST /a2a (JSON-RPC 2.0)| A2ARouter["A2A Task Router (a2a.py)"]
        StudioUI -->|REST /v1/*| RESTAPI["REST API Router (server.py)"]
    end

    subgraph InternalMesh ["Internal Agent Delegation Mesh"]
        A2ARouter & MCPHandler --> Graph["BotmartzDelegationGraph Master Orchestrator"]
        Graph --> Arch["botmartz-architect (Rust Core & Triad Storage)"]
        Graph --> Parser["botmartz-parser (Docling AST & JEV Late Chunking)"]
        Graph --> Router["botmartz-inference (Hybrid RRF & CAG Radix KV-Cache)"]
        Graph --> Sentinel["botmartz-sentinel (Evidence-Grounded Abstention Gate)"]
        Graph --> Support["openai-support-agent (Reasoning, Vision OCR & NL-to-SQL)"]
    end

    subgraph StorageTriad ["Zero-Sprawl Storage Triad"]
        Graph --> Lance["LanceDB (Arrow Vectors)"]
        Graph --> Tantivy["Tantivy / BM25 (Lexical)"]
        Graph --> Duck["DuckDB (Deterministic KAG SQL)"]
    end
```

---

## 2. A2A (Agent-to-Agent) Protocol Specification

VORTEX implements the standard Agent-to-Agent protocol specification allowing autonomous agents across organizations to discover capabilities, inspect agent cards, and delegate long-running tasks.

### 2.1 Agent Card Discovery (`GET /.well-known/agent.json`)
The Agent Card provides machine-readable metadata detailing capabilities, input/output modes, and subagent rosters:

```json
{
  "name": "Botmartz VORTEX Omni-RAG Engine",
  "description": "Sovereign In-House Enterprise Omni-RAG & Autonomous Generation Engine by Botmartz AI Solutions Pvt. Ltd...",
  "url": "http://localhost:8420",
  "version": "0.1.0",
  "provider": {
    "organization": "Botmartz AI Solutions Private Limited",
    "url": "https://botmartz.com"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "skills": [
    {
      "id": "vortex-omni-rag-query",
      "name": "Hybrid H-RAG + JEV + CAG + KAG Query",
      "tags": ["rag", "kag", "cag", "jev", "duckdb", "sentinel"]
    },
    {
      "id": "vortex-ast-merkle-ingest",
      "name": "Layout-Aware Ingestion & Merkle Diffing",
      "tags": ["docling", "ocr", "merkle", "ast"]
    },
    {
      "id": "vortex-kag-sql",
      "name": "Deterministic DuckDB KAG Analytics",
      "tags": ["duckdb", "sql", "kag"]
    }
  ],
  "subagents": [
    {"id": "botmartz-architect", "name": "Botmartz Architect", "role": "Lead Systems, Rust Core & Triad Storage"},
    {"id": "botmartz-parser", "name": "Botmartz Parser & OCR", "role": "Docling Layout AST & JEV Embeddings"},
    {"id": "botmartz-inference", "name": "Botmartz Inference Router", "role": "CAG Radix KV-Cache & DuckDB KAG"},
    {"id": "botmartz-sentinel", "name": "Evaluation Sentinel", "role": "Evidence-Grounded Abstention Gate"},
    {"id": "openai-support-agent", "name": "OpenAI Supportive Agent", "role": "Vision OCR & NL-to-SQL Translation"}
  ]
}
```

### 2.2 JSON-RPC 2.0 Router (`POST /a2a`)
The `/a2a` endpoint processes standard JSON-RPC 2.0 envelopes for asynchronous and synchronous multi-agent collaboration:

1. **`agents/list`**:
   - Lists all registered internal agents, their capabilities, and skill sets.
2. **`tasks/send`**:
   - Submits a task to a targeted subagent (e.g., `agentId: "botmartz-parser"` for document ingestion or `agentId: "botmartz-inference"` for hybrid query).
   - Returns a structured task execution record with lifecycle state (`completed`, `working`, `failed`, `canceled`), message history, and artifact payloads.
3. **`tasks/get`**:
   - Queries the execution state and results of an existing task by `task_id`.
4. **`tasks/cancel`**:
   - Cancels an in-flight background task execution.

#### Sample `tasks/send` Request
```json
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "method": "tasks/send",
  "params": {
    "agentId": "botmartz-inference",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "What is the total GPU VRAM across all sovereign cluster nodes?"}]
    }
  }
}
```

#### Sample `tasks/send` Response
```json
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "result": {
    "id": "task-7c8a14b9",
    "status": {
      "state": "completed",
      "timestamp": "2026-11-14T07:15:00Z",
      "message": {
        "role": "agent",
        "parts": [{"type": "text", "text": "The total GPU VRAM across all sovereign cluster nodes is 120 GB (verified across 3 nodes)."}]
      }
    },
    "artifacts": [
      {
        "name": "vortex_structured_output",
        "parts": [{
          "type": "data",
          "data": {
            "verified": true,
            "groundedness_score": 0.99,
            "merkle_provenance_chain": ["c3f8..."],
            "kag_deterministic_rows": 1
          }
        }]
      }
    ]
  }
}
```

---

## 3. Native Model Context Protocol (MCP) Server

Botmartz VORTEX exposes native MCP tools over two primary transports:
1. **Streamable HTTP Gateway**: `POST http://localhost:8420/mcp`
2. **Local Stdio Transport**: `python -m botmartz_engine.api.mcp_server` (registered in `~/.gemini/config/mcp_config.json`)

### 3.1 Exposed MCP Tools Catalog

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `vortex_ingest_document` | `doc_id`, `uri`, `markdown_text`, `version` | Parses document into `DocumentAST`, computes Merkle diff, extracts DuckDB tables, and indexes JEV vectors. |
| `vortex_hybrid_query` | `query`, `sql_override`, `provider` | Executes hybrid retrieval across H-RAG, JEV, DuckDB SQL, and CAG Radix KV-cache with Sentinel verification. |
| `vortex_kag_sql_query` | `sql` | Executes deterministic read-only analytical SQL against extracted DuckDB KAG tables. |
| `vortex_inspect_ast_merkle` | `doc_id` | Returns the full hierarchical AST tree and cryptographic Merkle node hashes for an indexed document. |
| `vortex_a2a_delegate` | `agent_id`, `text` | Delegates a task to an internal VORTEX subagent via the A2A protocol bridge. |
| `vortex_model_vault_status` | *(none)* | Inspects local `/mnt/ai_vault/models` downloads, Ollama status, and CAG Radix cache telemetry. |

### 3.2 MCP Tool Call Protocol Example
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "vortex_kag_sql_query",
    "arguments": {
      "sql": "SELECT node_id, gpu_vram_gb FROM sovereign_workstation_specs WHERE gpu_vram_gb >= 24"
    }
  }
}
```
**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\n  \"rows\": [\n    {\"node_id\": \"workstation-alpha\", \"gpu_vram_gb\": 48},\n    {\"node_id\": \"workstation-beta\", \"gpu_vram_gb\": 48},\n    {\"node_id\": \"workstation-gamma\", \"gpu_vram_gb\": 24}\n  ],\n  \"row_count\": 3\n}"
      }
    ],
    "isError": false
  }
}
```

---

## 4. Security & Sovereign Governance

> [!CAUTION]
> **Deterministic Read-Only SQL Policy**: The DuckDB execution bridge strictly prohibits destructive SQL mutations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `COPY`). Only `SELECT` and `WITH ... SELECT` queries are allowed to execute.

- **Air-Gapped Operation**: Both A2A and MCP endpoints run natively on localhost (`127.0.0.1:8420`) or inside a private enterprise VPC with zero mandatory external internet connections.
- **Cryptographic Provenance**: Every tool response carries the root `BLAKE3` Merkle hash of the underlying document state to guarantee that responses are traceable to exact document revisions.

---

## 5. Linked Specifications
- **[[00-MOC/System-Architecture-MOC|System Architecture MOC]]**
- **[[01-Architecture-Specs/04-Agent-Delegation-Graph-and-MCP|04 — Agent Delegation Graph & Native MCP Server]]**
- **[[01-Architecture-Specs/06-Docling-OCR-and-Vision-AST|06 — Docling OCR & Vision AST Layout Parser]]**
- **[[01-Architecture-Specs/08-Skills-and-Subagents-Catalog|08 — Skills & Subagents Catalog]]**
- **[[02-RFCs/RFC-001-Surpassing-Traditional Multi-Container RAG-Benchmark|RFC-001 — Surpassing Traditional Multi-Container RAG Benchmark]]**
- **[[04-Daily-Logs/2026-11-14-Full-VORTEX-Engine-Build-and-Test|2026-11-14 — Full VORTEX Engine Build & Test Log]]**
