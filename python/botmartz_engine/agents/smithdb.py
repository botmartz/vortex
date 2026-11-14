"""SmithDB: Thread-safe Agent State, Pregel Checkpoints, Traces, KBs, Connectors & Feedback Store.

Architecture Note:
    Runs zero-sprawl embedded SQLite (WAL mode) by default for instant single-node developer UX,
    with identical relational schema semantics ready for PostgreSQL (via psycopg/asyncpg) when scaling
    horizontally across stateless API replicas.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings


class VortexSmithDB:
    """Persistent store for Managed Agents, Pregel BSP Checkpoints, Smith Traces, KBs & Feedback."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else (settings.data_dir / "vortex_smithdb.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._init_schema()
            self._seed_defaults()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS managed_agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                topology TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                tools_json TEXT NOT NULL,
                kb_ids_json TEXT NOT NULL,
                max_steps INTEGER NOT NULL DEFAULT 8,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pregel_checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                superstep INTEGER NOT NULL,
                node_name TEXT NOT NULL,
                state_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cp_thread ON pregel_checkpoints(thread_id, superstep);

            CREATE TABLE IF NOT EXISTS smith_traces (
                trace_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                query TEXT NOT NULL,
                verdict TEXT NOT NULL,
                total_latency_ms REAL NOT NULL,
                total_tokens INTEGER NOT NULL,
                mcsd_speedup_x REAL NOT NULL,
                ear_entropy REAL NOT NULL,
                spans_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_bases (
                kb_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                chunk_preset TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_connectors (
                connector_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                model_name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS developer_feedback (
                feedback_id TEXT PRIMARY KEY,
                trace_id TEXT,
                reviewer TEXT NOT NULL,
                organization TEXT NOT NULL,
                rating INTEGER NOT NULL,
                category TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    def _seed_defaults(self) -> None:
        now = time.time()
        agent_count = self._conn.execute("SELECT COUNT(*) FROM managed_agents").fetchone()[0]
        if agent_count == 0:
            default_agents = [
                (
                    "vortex-deep-supervisor",
                    "VORTEX Deep Supervisor",
                    "Multi-Agent Pregel Orchestrator",
                    "pregel_supervisor",
                    "openai",
                    settings.openai_model,
                    "Coordinate EAR retrieval routing, DuckDB KAG SQL analytics, MCSD drafting, and SCG verification.",
                    json.dumps([
                        "tool_navigate_ast_tree",
                        "tool_hybrid_ear_search",
                        "tool_duckdb_kag_sql",
                        "tool_merkle_diff_audit",
                        "tool_subagent_handoff",
                    ]),
                    json.dumps(["kb-enterprise-core", "kb-financial-olap"]),
                    8,
                    now,
                ),
                (
                    "vortex-sql-quant",
                    "DuckDB KAG Quant Analyst",
                    "Deterministic Tabular & SQL Specialist",
                    "react_tool_loop",
                    "openai",
                    settings.openai_model,
                    "Execute read-only analytical DuckDB queries over structured tables without floating-point hallucinations.",
                    json.dumps(["tool_duckdb_kag_sql", "tool_grep_exact_chunks"]),
                    json.dumps(["kb-financial-olap"]),
                    6,
                    now,
                ),
                (
                    "vortex-compliance-auditor",
                    "SCG & Merkle Compliance Auditor",
                    "Claim Verification & Abstention Gate",
                    "verification_gate",
                    "ollama",
                    settings.ollama_model,
                    "Verify atomic answer claims against BLAKE3 AST hashes and force abstention if ungrounded.",
                    json.dumps(["tool_merkle_diff_audit", "tool_navigate_ast_tree"]),
                    json.dumps(["kb-enterprise-core", "kb-ragflow-duel"]),
                    4,
                    now,
                ),
                (
                    "vortex-research-navigator",
                    "JEV Tree Research Navigator",
                    "Long-Horizon Hierarchical Tree Explorer",
                    "plan_execute",
                    "openai",
                    settings.openai_model,
                    "Traverse parent-child AST sections and assemble global-context JEV spans across large filings.",
                    json.dumps(["tool_hybrid_ear_search", "tool_navigate_ast_tree", "tool_grep_exact_chunks"]),
                    json.dumps(["kb-enterprise-core"]),
                    10,
                    now,
                ),
            ]
            self._conn.executemany(
                """
                INSERT INTO managed_agents
                (agent_id, name, role, topology, provider, model, system_prompt, tools_json, kb_ids_json, max_steps, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                default_agents,
            )

        kb_count = self._conn.execute("SELECT COUNT(*) FROM knowledge_bases").fetchone()[0]
        if kb_count == 0:
            default_kbs = [
                (
                    "kb-enterprise-core",
                    "Enterprise Technical Specs",
                    "hrag_jev",
                    "Hierarchical AST parsing + JEV Late Chunking for architecture specs, manuals, and PDFs.",
                    now,
                ),
                (
                    "kb-financial-olap",
                    "Financial & SQL OLAP Vault",
                    "table_olap",
                    "Structured spreadsheets, SQLite/PostgreSQL imports, and Markdown tables auto-mapped to DuckDB.",
                    now,
                ),
                (
                    "kb-ragflow-duel",
                    "Side-by-Side Eval Corpus",
                    "general",
                    "Reference corpus used to benchmark RAGFlow DeepDoc/AgenticRAG against Botmartz VORTEX.",
                    now,
                ),
            ]
            self._conn.executemany(
                "INSERT INTO knowledge_bases (kb_id, name, chunk_preset, description, created_at) VALUES (?, ?, ?, ?, ?)",
                default_kbs,
            )

        conn_count = self._conn.execute("SELECT COUNT(*) FROM model_connectors").fetchone()[0]
        if conn_count == 0:
            default_connectors = [
                (
                    "openai-default",
                    "OpenAI Compatible / Cloud Support",
                    "openai",
                    "https://api.openai.com/v1",
                    settings.openai_model,
                    1 if settings.openai_api_key else 0,
                    json.dumps({"supports_vision": True, "supports_tools": True}),
                    now,
                ),
                (
                    "ollama-local",
                    "Ollama Endpoint",
                    "ollama",
                    settings.ollama_base_url,
                    settings.ollama_model,
                    1,
                    json.dumps({"supports_local_privacy": True}),
                    now,
                ),
                (
                    "sglang-cluster",
                    "SGLang RadixAttention Serving",
                    "sglang",
                    settings.sglang_base_url or "http://127.0.0.1:30000",
                    "Qwen/Qwen3-30B-A3B-FP8",
                    1,
                    json.dumps({"kv_cache": "RadixAttention", "grammar": "xgrammar"}),
                    now,
                ),
                (
                    "vllm-cluster",
                    "vLLM PagedAttention + APC",
                    "vllm",
                    settings.vllm_base_url or "http://127.0.0.1:8001",
                    settings.vllm_model or "Qwen/Qwen3-30B-A3B-FP8",
                    1,
                    json.dumps({"kv_cache": "AutomaticPrefixCaching", "speculative": True}),
                    now,
                ),
                (
                    "llamacpp-local",
                    "llama.cpp OpenAI-Compatible Server",
                    "llamacpp",
                    "http://127.0.0.1:8081",
                    "local-gguf",
                    1,
                    json.dumps({"cache_reuse": 256}),
                    now,
                ),
            ]
            self._conn.executemany(
                """
                INSERT INTO model_connectors
                (connector_id, name, provider_type, base_url, model_name, enabled, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                default_connectors,
            )

        self._conn.commit()

    # ------------------------------------------------------------------
    # Managed Agents API
    # ------------------------------------------------------------------
    def _row_to_agent(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "agent_id": row["agent_id"],
            "name": row["name"],
            "role": row["role"],
            "topology": row["topology"],
            "provider": row["provider"],
            "model": row["model"],
            "system_prompt": row["system_prompt"],
            "tools": json.loads(row["tools_json"]),
            "kb_ids": json.loads(row["kb_ids_json"]),
            "max_steps": row["max_steps"],
            "created_at": row["created_at"],
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM managed_agents ORDER BY created_at ASC").fetchall()
            return [self._row_to_agent(r) for r in rows]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM managed_agents WHERE agent_id = ?", (agent_id,)).fetchone()
            return self._row_to_agent(row) if row else None

    def upsert_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        topology: str = "pregel_supervisor",
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        system_prompt: str = "",
        tools: Optional[List[str]] = None,
        kb_ids: Optional[List[str]] = None,
        max_steps: int = 8,
    ) -> Dict[str, Any]:
        clean_id = agent_id.strip() or f"agent-{uuid.uuid4().hex[:8]}"
        now = time.time()
        tools_list = tools if tools is not None else ["tool_hybrid_ear_search", "tool_duckdb_kag_sql"]
        kbs_list = kb_ids if kb_ids is not None else ["kb-enterprise-core"]
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO managed_agents
                (agent_id, name, role, topology, provider, model, system_prompt, tools_json, kb_ids_json, max_steps, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    name=excluded.name,
                    role=excluded.role,
                    topology=excluded.topology,
                    provider=excluded.provider,
                    model=excluded.model,
                    system_prompt=excluded.system_prompt,
                    tools_json=excluded.tools_json,
                    kb_ids_json=excluded.kb_ids_json,
                    max_steps=excluded.max_steps
                """,
                (
                    clean_id,
                    name.strip(),
                    role.strip(),
                    topology.strip(),
                    provider.strip(),
                    model.strip(),
                    system_prompt.strip(),
                    json.dumps(tools_list),
                    json.dumps(kbs_list),
                    max(1, int(max_steps)),
                    now,
                ),
            )
            self._conn.commit()
        return self.get_agent(clean_id) or {}

    # ------------------------------------------------------------------
    # Pregel Checkpoints & Time-Travel Replay
    # ------------------------------------------------------------------
    def save_checkpoint(
        self,
        thread_id: str,
        agent_id: str,
        superstep: int,
        node_name: str,
        state: Dict[str, Any],
        status: str = "completed",
    ) -> Dict[str, Any]:
        cp_id = f"cp-{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO pregel_checkpoints
                (checkpoint_id, thread_id, agent_id, superstep, node_name, state_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cp_id, thread_id, agent_id, superstep, node_name, json.dumps(state, default=str), status, now),
            )
            self._conn.commit()
        return {
            "checkpoint_id": cp_id,
            "thread_id": thread_id,
            "agent_id": agent_id,
            "superstep": superstep,
            "node_name": node_name,
            "status": status,
            "created_at": now,
        }

    def list_checkpoints(self, thread_id: Optional[str] = None, limit: int = 40) -> List[Dict[str, Any]]:
        with self._lock:
            if thread_id:
                rows = self._conn.execute(
                    "SELECT * FROM pregel_checkpoints WHERE thread_id = ? ORDER BY created_at DESC LIMIT ?",
                    (thread_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM pregel_checkpoints ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                {
                    "checkpoint_id": r["checkpoint_id"],
                    "thread_id": r["thread_id"],
                    "agent_id": r["agent_id"],
                    "superstep": r["superstep"],
                    "node_name": r["node_name"],
                    "state": json.loads(r["state_json"]),
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._conn.execute(
                "SELECT * FROM pregel_checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)
            ).fetchone()
            if not r:
                return None
            return {
                "checkpoint_id": r["checkpoint_id"],
                "thread_id": r["thread_id"],
                "agent_id": r["agent_id"],
                "superstep": r["superstep"],
                "node_name": r["node_name"],
                "state": json.loads(r["state_json"]),
                "status": r["status"],
                "created_at": r["created_at"],
            }

    # ------------------------------------------------------------------
    # SmithDB Execution Traces & Spans
    # ------------------------------------------------------------------
    def record_trace(
        self,
        thread_id: str,
        agent_id: str,
        query: str,
        verdict: str,
        total_latency_ms: float,
        total_tokens: int,
        mcsd_speedup_x: float,
        ear_entropy: float,
        spans: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = trace_id or f"tr-{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO smith_traces
                (trace_id, thread_id, agent_id, query, verdict, total_latency_ms, total_tokens,
                 mcsd_speedup_x, ear_entropy, spans_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tid,
                    thread_id,
                    agent_id,
                    query,
                    verdict,
                    round(float(total_latency_ms), 2),
                    int(total_tokens),
                    round(float(mcsd_speedup_x), 2),
                    round(float(ear_entropy), 3),
                    json.dumps(spans, default=str),
                    now,
                ),
            )
            self._conn.commit()
        return self.get_trace(tid) or {}

    def list_traces(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM smith_traces ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "trace_id": r["trace_id"],
                    "thread_id": r["thread_id"],
                    "agent_id": r["agent_id"],
                    "query": r["query"],
                    "verdict": r["verdict"],
                    "total_latency_ms": r["total_latency_ms"],
                    "total_tokens": r["total_tokens"],
                    "mcsd_speedup_x": r["mcsd_speedup_x"],
                    "ear_entropy": r["ear_entropy"],
                    "spans": json.loads(r["spans_json"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._conn.execute("SELECT * FROM smith_traces WHERE trace_id = ?", (trace_id,)).fetchone()
            if not r:
                return None
            return {
                "trace_id": r["trace_id"],
                "thread_id": r["thread_id"],
                "agent_id": r["agent_id"],
                "query": r["query"],
                "verdict": r["verdict"],
                "total_latency_ms": r["total_latency_ms"],
                "total_tokens": r["total_tokens"],
                "mcsd_speedup_x": r["mcsd_speedup_x"],
                "ear_entropy": r["ear_entropy"],
                "spans": json.loads(r["spans_json"]),
                "created_at": r["created_at"],
            }

    # ------------------------------------------------------------------
    # Knowledge Bases
    # ------------------------------------------------------------------
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM knowledge_bases ORDER BY created_at ASC").fetchall()
            return [dict(r) for r in rows]

    def create_knowledge_base(
        self,
        kb_id: str,
        name: str,
        chunk_preset: str = "hrag_jev",
        description: str = "",
    ) -> Dict[str, Any]:
        clean_id = kb_id.strip() or f"kb-{uuid.uuid4().hex[:8]}"
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO knowledge_bases (kb_id, name, chunk_preset, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(kb_id) DO UPDATE SET
                    name=excluded.name,
                    chunk_preset=excluded.chunk_preset,
                    description=excluded.description
                """,
                (clean_id, name.strip(), chunk_preset.strip(), description.strip(), now),
            )
            self._conn.commit()
            row = self._conn.execute("SELECT * FROM knowledge_bases WHERE kb_id = ?", (clean_id,)).fetchone()
            return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Model & Inference Connectors
    # ------------------------------------------------------------------
    def _row_to_connector(self, r: sqlite3.Row) -> Dict[str, Any]:
        return {
            "connector_id": r["connector_id"],
            "name": r["name"],
            "provider_type": r["provider_type"],
            "base_url": r["base_url"],
            "model_name": r["model_name"],
            "enabled": bool(r["enabled"]),
            "config": json.loads(r["config_json"]),
            "created_at": r["created_at"],
        }

    def list_connectors(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM model_connectors ORDER BY created_at ASC").fetchall()
            return [self._row_to_connector(r) for r in rows]

    def get_connector(self, connector_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM model_connectors WHERE connector_id = ?", (connector_id,)
            ).fetchone()
            return self._row_to_connector(row) if row else None

    def upsert_connector(
        self,
        connector_id: str,
        name: str,
        provider_type: str,
        base_url: str,
        model_name: str,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        clean_id = connector_id.strip() or f"conn-{uuid.uuid4().hex[:8]}"
        now = time.time()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO model_connectors
                (connector_id, name, provider_type, base_url, model_name, enabled, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connector_id) DO UPDATE SET
                    name=excluded.name,
                    provider_type=excluded.provider_type,
                    base_url=excluded.base_url,
                    model_name=excluded.model_name,
                    enabled=excluded.enabled,
                    config_json=excluded.config_json
                """,
                (
                    clean_id,
                    name.strip(),
                    provider_type.strip(),
                    base_url.strip().rstrip("/"),
                    model_name.strip(),
                    1 if enabled else 0,
                    json.dumps(config or {}),
                    now,
                ),
            )
            self._conn.commit()
        return self.get_connector(clean_id) or {}

    # ------------------------------------------------------------------
    # Developer & Enterprise Feedback
    # ------------------------------------------------------------------
    def add_feedback(
        self,
        reviewer: str,
        rating: int,
        category: str,
        comment: str,
        trace_id: Optional[str] = None,
        organization: str = "External Evaluator",
    ) -> Dict[str, Any]:
        fb_id = f"fb-{uuid.uuid4().hex[:10]}"
        now = time.time()
        bounded_rating = max(1, min(5, int(rating)))
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO developer_feedback
                (feedback_id, trace_id, reviewer, organization, rating, category, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fb_id,
                    trace_id,
                    reviewer.strip() or "Anonymous Dev",
                    organization.strip() or "External Evaluator",
                    bounded_rating,
                    category.strip() or "general",
                    comment.strip(),
                    now,
                ),
            )
            self._conn.commit()
            row = self._conn.execute("SELECT * FROM developer_feedback WHERE feedback_id = ?", (fb_id,)).fetchone()
            return dict(row) if row else {}

    def list_feedback(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM developer_feedback ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "storage_backend": "sqlite3_wal (PostgreSQL-ready relational schema)",
                "db_path": str(self.db_path),
                "managed_agents": self._conn.execute("SELECT COUNT(*) FROM managed_agents").fetchone()[0],
                "pregel_checkpoints": self._conn.execute("SELECT COUNT(*) FROM pregel_checkpoints").fetchone()[0],
                "traces": self._conn.execute("SELECT COUNT(*) FROM smith_traces").fetchone()[0],
                "knowledge_bases": self._conn.execute("SELECT COUNT(*) FROM knowledge_bases").fetchone()[0],
                "connectors": self._conn.execute("SELECT COUNT(*) FROM model_connectors").fetchone()[0],
                "feedback_entries": self._conn.execute("SELECT COUNT(*) FROM developer_feedback").fetchone()[0],
            }
