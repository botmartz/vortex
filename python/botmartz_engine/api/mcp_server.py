"""Native Model Context Protocol (MCP) Server for Botmartz VORTEX.

Supports both:
1. Streamable HTTP (`POST /mcp` inside FastAPI)
2. Local `stdio` transport (`python -m botmartz_engine.api.mcp_server`)
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from ..agents import BotmartzDelegationGraph
from .a2a import A2ATaskStore


MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "vortex_ingest_document",
        "description": "Ingest Markdown/text/tables into Botmartz VORTEX H-RAG AST, compute BLAKE3 Merkle diff, extract tables to DuckDB, and index JEV Late-Chunking spans.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string"},
                "uri": {"type": "string"},
                "markdown_text": {"type": "string"},
                "version": {"type": "integer", "default": 1},
            },
            "required": ["doc_id", "markdown_text"],
        },
    },
    {
        "name": "vortex_hybrid_query",
        "description": "Query Botmartz VORTEX across H-RAG, JEV Late Chunking, DuckDB KAG SQL, CAG Radix KV-Cache, and Evaluation Sentinel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "sql_override": {"type": "string"},
                "provider": {"type": "string", "default": "openai"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "vortex_kag_sql_query",
        "description": "Execute deterministic read-only SELECT/WITH SQL queries against DuckDB KAG extracted tables.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "vortex_inspect_ast_merkle",
        "description": "Inspect the Hierarchical Document Tree (DocumentAST) and Merkle hashes for an indexed document.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "vortex_a2a_delegate",
        "description": "Delegate a task to a specialized Botmartz VORTEX A2A agent (botmartz-architect, botmartz-parser, botmartz-inference).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "default": "botmartz-inference"},
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "vortex_model_vault_status",
        "description": "Inspect local /mnt/ai_vault/models downloads, Ollama status, OpenAI connectivity, and CAG Radix cache telemetry.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_mcp_jsonrpc(
    payload: Dict[str, Any],
    engine_graph: BotmartzDelegationGraph,
    a2a_store: A2ATaskStore,
) -> Dict[str, Any]:
    req_id = payload.get("id")
    method = payload.get("method", "")
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}},
                "serverInfo": {"name": "botmartz-vortex-mcp", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

    if method == "resources/list":
        resources = [
            {
                "uri": f"vortex://ast/{doc_id}",
                "name": f"DocumentAST: {doc_id}",
                "mimeType": "application/json",
            }
            for doc_id in engine_graph.state.documents.keys()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources}}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            if name == "vortex_ingest_document":
                res = engine_graph.ingest_markdown(
                    doc_id=args["doc_id"],
                    uri=args.get("uri", f"mcp://{args['doc_id']}.md"),
                    markdown_text=args["markdown_text"],
                    version=int(args.get("version", 1)),
                )
            elif name == "vortex_hybrid_query":
                res = engine_graph.query(
                    query=args["query"],
                    sql_override=args.get("sql_override"),
                    provider=args.get("provider", "openai"),
                )
            elif name == "vortex_kag_sql_query":
                rows = engine_graph.state.table_mapper.execute_readonly_sql(args["sql"])
                res = {"rows": rows, "row_count": len(rows)}
            elif name == "vortex_inspect_ast_merkle":
                doc = engine_graph.state.documents.get(args["doc_id"])
                if not doc:
                    res = {"error": f"Document '{args['doc_id']}' not found"}
                else:
                    res = doc.model_dump(mode="json")
            elif name == "vortex_a2a_delegate":
                res = a2a_store.handle_jsonrpc(
                    {
                        "jsonrpc": "2.0",
                        "id": "mcp-a2a",
                        "method": "tasks/send",
                        "params": {
                            "agentId": args.get("agent_id", "botmartz-inference"),
                            "message": {"role": "user", "parts": [{"type": "text", "text": args["text"]}]},
                        },
                    },
                    engine_graph=engine_graph,
                )
            elif name == "vortex_model_vault_status":
                res = {
                    "providers": engine_graph.router_agent.inference_engine.inspect_ai_vault_and_providers(),
                    "duckdb_tables": engine_graph.state.store.list_duckdb_tables(),
                    "documents": list(engine_graph.state.documents.keys()),
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool '{name}'"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2, default=str)}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unsupported MCP method '{method}'"},
    }


def run_stdio_server() -> None:
    """Run Botmartz VORTEX MCP server over stdin/stdout JSON-RPC."""
    from .seed import seed_default_corpus

    engine_graph = BotmartzDelegationGraph(prefer_openai=False)
    seed_default_corpus(engine_graph)
    a2a_store = A2ATaskStore()

    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        response = handle_mcp_jsonrpc(payload, engine_graph=engine_graph, a2a_store=a2a_store)
        if payload.get("id") is not None:
            sys.stdout.write(json.dumps(response, default=str) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
