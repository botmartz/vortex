"""Agent-to-Agent (A2A) Protocol Server Implementation for Botmartz VORTEX.

Exposes:
- `GET /.well-known/agent.json`: Standard A2A Agent Card
- `POST /a2a`: JSON-RPC 2.0 router (`tasks/send`, `tasks/get`, `tasks/cancel`, `agents/list`)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class A2ATaskStore:
    """In-memory A2A task ledger and multi-agent registry."""

    AGENTS = [
        {
            "id": "botmartz-architect",
            "name": "Botmartz Architect",
            "role": "Lead Systems, Rust Core, LanceDB/DuckDB Triad & MCP Orchestrator",
            "skills": ["rust-merkle-ast", "storage-triad", "mcp-routing"],
        },
        {
            "id": "botmartz-parser",
            "name": "Botmartz Parser & OCR",
            "role": "Docling-style Layout AST, PyMuPDF/RapidOCR/Vision OCR & JEV Late-Chunking",
            "skills": ["docling-ocr", "hrag-ast-parsing", "jev-late-chunking"],
        },
        {
            "id": "botmartz-inference",
            "name": "Botmartz Inference Router",
            "role": "CAG RadixAttention Prefix Caching, KAG DuckDB NL-to-SQL & vLLM/SGLang",
            "skills": ["cag-radix-cache", "kag-duckdb-sql", "vllm-sglang"],
        },
        {
            "id": "botmartz-sentinel",
            "name": "Evaluation Sentinel",
            "role": "Evidence-Grounded Abstention Gate & BLAKE3 Merkle Provenance Verifier",
            "skills": ["sentinel-abstention", "merkle-provenance"],
        },
        {
            "id": "openai-support-agent",
            "name": "OpenAI Supportive Reasoning Agent",
            "role": "GPT-4o-mini Vision OCR, NL-to-SQL Translation & Grounded Synthesis",
            "skills": ["openai-vision-ocr", "openai-nl2sql", "openai-synthesis"],
        },
    ]

    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def get_agent_card(self, base_url: str = "http://localhost:8420") -> Dict[str, Any]:
        return {
            "name": "Botmartz VORTEX Omni-RAG Engine",
            "description": (
                "Sovereign In-House Enterprise Omni-RAG & Autonomous Generation Engine by Botmartz AI Solutions Pvt. Ltd. "
                "Combines Hierarchical AST (H-RAG), Late Chunking (JEV), RadixAttention (CAG), Embedded DuckDB (KAG), "
                "Cryptographic Merkle Diffing, and Evidence-Grounded Abstention."
            ),
            "url": base_url.rstrip("/"),
            "version": "0.1.0",
            "provider": {
                "organization": "Botmartz AI Solutions Private Limited",
                "url": "https://botmartz.com",
            },
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": True,
            },
            "defaultInputModes": ["text/plain", "application/json"],
            "defaultOutputModes": ["text/plain", "application/json"],
            "skills": [
                {
                    "id": "vortex-omni-rag-query",
                    "name": "Hybrid H-RAG + JEV + CAG + KAG Query",
                    "description": "Execute hybrid retrieval, DuckDB SQL KAG, Radix CAG synthesis, and Sentinel verification.",
                    "tags": ["rag", "kag", "cag", "jev", "duckdb", "sentinel"],
                },
                {
                    "id": "vortex-ast-merkle-ingest",
                    "name": "Layout-Aware Ingestion & Merkle Diffing",
                    "description": "Ingest documents/tables/OCR into H-RAG DocumentAST with surgical Merkle deltas.",
                    "tags": ["docling", "ocr", "merkle", "ast"],
                },
                {
                    "id": "vortex-kag-sql",
                    "name": "Deterministic DuckDB KAG Analytics",
                    "description": "Run read-only analytical SQL across extracted document tables.",
                    "tags": ["duckdb", "sql", "kag"],
                },
            ],
            "subagents": self.AGENTS,
        }

    def handle_jsonrpc(self, payload: Dict[str, Any], engine_graph: Any) -> Dict[str, Any]:
        req_id = payload.get("id")
        method = payload.get("method", "")
        params = payload.get("params") or {}

        if method == "agents/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"agents": self.AGENTS},
            }

        if method == "tasks/send":
            task_id = params.get("id") or f"task-{uuid.uuid4().hex[:12]}"
            target_agent = params.get("agentId", "botmartz-inference")
            message = params.get("message") or {}
            parts = message.get("parts") or []
            user_text = ""
            for p in parts:
                if isinstance(p, dict) and p.get("type") == "text":
                    user_text += p.get("text", "")
            if not user_text:
                user_text = params.get("query") or ""

            now = datetime.now(timezone.utc).isoformat()
            if target_agent == "botmartz-architect":
                tables = engine_graph.state.store.list_duckdb_tables()
                vault = engine_graph.router_agent.inference_engine.inspect_ai_vault_and_providers()
                result_data: Dict[str, Any] = {
                    "agent": target_agent,
                    "documents_indexed": list(engine_graph.state.documents.keys()),
                    "duckdb_tables": tables,
                    "ai_vault_providers": vault,
                }
                summary_text = (
                    f"[botmartz-architect] Active docs={len(result_data['documents_indexed'])}, "
                    f"DuckDB tables={len(tables)}, LanceDB={'connected' if engine_graph.state.store.lancedb_connected else 'fallback'}."
                )
            elif target_agent == "botmartz-parser":
                doc_id = params.get("doc_id") or f"a2a_doc_{uuid.uuid4().hex[:6]}"
                ingest_res = engine_graph.ingest_markdown(
                    doc_id=doc_id,
                    uri=f"a2a://{doc_id}.md",
                    markdown_text=user_text,
                    version=int(params.get("version", 1)),
                )
                result_data = ingest_res
                summary_text = (
                    f"[botmartz-parser] Parsed '{doc_id}' into {ingest_res['ast_node_count']} AST nodes, "
                    f"{ingest_res['jev_chunk_count']} JEV spans, root={ingest_res['root_merkle_hash'][:12]}."
                )
            else:
                # Default: run full Omni-RAG + Evaluation Sentinel delegation graph
                provider = params.get("provider", "openai")
                sql_override = params.get("sql_override")
                query_res = engine_graph.query(
                    query=user_text,
                    sql_override=sql_override,
                    provider=provider,
                )
                result_data = query_res
                summary_text = query_res["result"]["answer"]

            task_record = {
                "id": task_id,
                "status": {
                    "state": "completed",
                    "timestamp": now,
                    "message": {
                        "role": "agent",
                        "parts": [{"type": "text", "text": summary_text}],
                    },
                },
                "artifacts": [
                    {
                        "name": "vortex_structured_output",
                        "parts": [{"type": "data", "data": result_data}],
                    }
                ],
                "history": [
                    message if message else {"role": "user", "parts": [{"type": "text", "text": user_text}]},
                    {"role": "agent", "parts": [{"type": "text", "text": summary_text}]},
                ],
                "metadata": {
                    "targetAgent": target_agent,
                    "protocol": "A2A/1.0",
                },
            }
            self.tasks[task_id] = task_record
            return {"jsonrpc": "2.0", "id": req_id, "result": task_record}

        if method == "tasks/get":
            task_id = params.get("id")
            task = self.tasks.get(task_id)
            if not task:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Task '{task_id}' not found"},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": task}

        if method == "tasks/cancel":
            task_id = params.get("id")
            task = self.tasks.get(task_id)
            if not task:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Task '{task_id}' not found"},
                }
            task["status"]["state"] = "canceled"
            return {"jsonrpc": "2.0", "id": req_id, "result": task}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not supported"},
        }
