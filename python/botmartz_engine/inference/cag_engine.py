"""CAG (Cache-Augmented Generation) RadixAttention KV-Cache Manager & Multi-Provider Inference Engine.

Supports:
- Deterministic 4-tier CAG prefix block assembly (System -> Corpus Skeleton -> Pinned AST -> Session)
- Live OpenAI API synthesis & NL-to-SQL KAG translation (via provided OPENAI_API_KEY)
- Local Ollama (`gpt-oss:120b-cloud`), vLLM APC, and SGLang RadixAttention endpoints
- Real-time AI Vault model scanner (`/mnt/ai_vault/models`)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..config import settings
from ..schemas.core import CAGPrefixBlock, DocumentAST, DuckDBTableSchema


SYSTEM_CONSTITUTION = (
    "You are Botmartz VORTEX (Verified Omni-RAG Tree & Execution Engine), built by Botmartz AI Solutions Pvt. Ltd. "
    "Rules: (1) Ground every factual statement strictly in the provided H-RAG/JEV evidence spans and DuckDB KAG SQL rows. "
    "(2) Cite evidence inline using [node_id | merkle_hash_prefix]. "
    "(3) If the evidence is missing or insufficient to answer the question, start your response verbatim with 'ABSTAINED:' and state what evidence is missing."
)


class CAGRadixManager:
    """Builds deterministic Merkle-keyed KV-cache prefix stacks for vLLM APC & SGLang RadixAttention."""

    def __init__(self) -> None:
        self.known_prefix_hashes: set[str] = set()
        self.total_queries: int = 0
        self.radix_cache_hits: int = 0
        self.cached_tokens_saved: int = 0

    def assemble_prefix_stack(
        self,
        documents: Dict[str, DocumentAST],
        table_schemas: Dict[str, DuckDBTableSchema],
        pinned_hits: List[Dict[str, Any]],
    ) -> Tuple[List[CAGPrefixBlock], Dict[str, Any]]:
        blocks: List[CAGPrefixBlock] = []

        sys_hash = hashlib.blake2b(SYSTEM_CONSTITUTION.encode("utf-8"), digest_size=16).hexdigest()
        blocks.append(
            CAGPrefixBlock(
                block_id="cag::system_constitution",
                tier="system",
                merkle_hash=sys_hash,
                token_count=max(1, len(SYSTEM_CONSTITUTION) // 4),
                content=SYSTEM_CONSTITUTION,
            )
        )

        # Tier 2: Corpus H-RAG Tree Skeletons + DuckDB Schema Catalog
        skeleton_parts: List[str] = []
        merkle_inputs: List[str] = []
        for doc_id in sorted(documents.keys()):
            ast = documents[doc_id]
            root_hash = ast.nodes[ast.root_id].merkle_hash or ""
            merkle_inputs.append(root_hash)
            lines = [f"Document {doc_id} (root={root_hash[:12]}):"]
            for n in list(ast.nodes.values())[:25]:
                if n.title:
                    lines.append(f"{'  ' * n.depth}- {n.title} [{n.node_id}]")
            skeleton_parts.append("\n".join(lines))

        if table_schemas:
            skeleton_parts.append("DuckDB KAG Tables:")
            for tbl_name in sorted(table_schemas.keys()):
                sch = table_schemas[tbl_name]
                cols = ", ".join(f"{c.name}:{c.sql_type}" for c in sch.columns)
                skeleton_parts.append(f"- {tbl_name} ({cols})")

        skeleton_text = "\n".join(skeleton_parts) or "No documents indexed yet."
        skeleton_hash = hashlib.blake2b(
            ("|".join(merkle_inputs) + "|" + skeleton_text).encode("utf-8"), digest_size=16
        ).hexdigest()
        blocks.append(
            CAGPrefixBlock(
                block_id="cag::corpus_skeleton",
                tier="corpus_skeleton",
                merkle_hash=skeleton_hash,
                token_count=max(1, len(skeleton_text) // 4),
                content=skeleton_text,
            )
        )

        # Tier 3: Pinned Retrieved AST Subtrees
        if pinned_hits:
            hit_text = "\n".join(
                f"[{h['node_id']} | {h['merkle_hash'][:12]}] ({' > '.join(h['structural_path'])})\n{h['content']}"
                for h in pinned_hits
            )
            hit_hash = hashlib.blake2b(hit_text.encode("utf-8"), digest_size=16).hexdigest()
            blocks.append(
                CAGPrefixBlock(
                    block_id="cag::pinned_ast_subtree",
                    tier="pinned_ast_subtree",
                    merkle_hash=hit_hash,
                    token_count=max(1, len(hit_text) // 4),
                    content=hit_text,
                )
            )

        self.total_queries += 1
        prefix_signature = f"{sys_hash}:{skeleton_hash}"
        cache_hit = prefix_signature in self.known_prefix_hashes
        cached_tokens = blocks[0].token_count + blocks[1].token_count
        if cache_hit:
            self.radix_cache_hits += 1
            self.cached_tokens_saved += cached_tokens
        else:
            self.known_prefix_hashes.add(prefix_signature)

        telemetry = {
            "radix_cache_hit": cache_hit,
            "prefix_signature": prefix_signature,
            "pinned_prefix_tokens": cached_tokens,
            "total_queries": self.total_queries,
            "total_hits": self.radix_cache_hits,
            "hit_rate_pct": round((self.radix_cache_hits / max(1, self.total_queries)) * 100.0, 1),
            "cumulative_tokens_saved": self.cached_tokens_saved,
        }
        return blocks, telemetry


class MultiProviderInferenceEngine:
    """Routes CAG + KAG synthesis across OpenAI, Ollama, vLLM/SGLang, and reports AI Vault models."""

    def translate_nl_to_sql(
        self,
        query: str,
        table_schemas: Dict[str, DuckDBTableSchema],
        use_llm: bool = True,
    ) -> Optional[str]:
        if not table_schemas:
            return None

        schema_desc = "\n".join(
            f'Table "{name}" (rows={sch.row_count}): columns = '
            + ", ".join(f'"{c.name}" {c.sql_type}' for c in sch.columns)
            for name, sch in table_schemas.items()
        )

        if use_llm and settings.openai_api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.openai_api_key)
                resp = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a DuckDB SQL translator. Given the DuckDB tables below and a user question, "
                                "if ANY part of the question asks about data, metrics, totals, averages, or comparisons stored in these tables, "
                                "output ONLY a single valid read-only DuckDB SELECT query (no markdown fences, no commentary). "
                                "Always double-quote table and column names. Never write a scalar subquery that can return multiple rows "
                                "(if querying two unrelated tables, join via CROSS JOIN on 1-row aggregates or query one primary table cleanly). "
                                "Only output NONE if none of the tables are relevant."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Schemas:\n{schema_desc}\n\nQuestion: {query}",
                        },
                    ],
                    max_tokens=220,
                    temperature=0.0,
                )
                sql_candidate = (resp.choices[0].message.content or "").strip()
                sql_candidate = re.sub(r"^```(?:sql)?|```$", "", sql_candidate, flags=re.IGNORECASE | re.MULTILINE).strip()
                if sql_candidate.upper() != "NONE" and sql_candidate.upper().startswith(("SELECT", "WITH")):
                    return sql_candidate
            except Exception:
                pass

        # Deterministic schema-matching SQL fallback
        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        q_lower = query.lower()
        best_table: Optional[DuckDBTableSchema] = None
        best_score = 0
        for name, sch in table_schemas.items():
            score = sum(1 for tok in re.findall(r"[a-z0-9]+", name.lower()) if len(tok) >= 3 and tok in q_tokens)
            for col in sch.columns:
                for part in col.name.lower().split("_"):
                    if len(part) >= 3 and part in q_tokens:
                        score += 2
            if score > best_score:
                best_score = score
                best_table = sch

        # Require minimum confident column or table name match
        if best_table is None or best_score < 2:
            return None

        numeric_cols = [c.name for c in best_table.columns if c.sql_type in {"BIGINT", "DOUBLE"}]
        # Check for multiple requested aggregates across columns (Issue #18)
        select_parts = ["COUNT(*) AS row_count"]
        wants_sum = any(w in q_lower for w in {"total", "sum"})
        wants_avg = any(w in q_lower for w in {"average", "avg", "mean"})
        wants_max = any(w in q_lower for w in {"maximum", "max", "highest"})
        wants_min = any(w in q_lower for w in {"minimum", "min", "lowest"})

        matched_num_cols = [
            c for c in numeric_cols
            if any(part in q_tokens for part in c.lower().split("_") if len(part) >= 3)
        ]
        target_cols = matched_num_cols if matched_num_cols else numeric_cols[:2]

        if target_cols and (wants_sum or wants_avg or wants_max or wants_min):
            for tc in target_cols:
                if wants_sum:
                    select_parts.append(f'SUM("{tc}") AS total_{tc}')
                if wants_avg:
                    select_parts.append(f'AVG("{tc}") AS avg_{tc}')
                if wants_max:
                    select_parts.append(f'MAX("{tc}") AS max_{tc}')
                if wants_min:
                    select_parts.append(f'MIN("{tc}") AS min_{tc}')
            return f'SELECT {", ".join(select_parts)} FROM "{best_table.table_name}"'

        # If question specifically mentions columns in this table, select them instead of blind SELECT *
        if matched_num_cols:
            col_list = ", ".join(f'"{c}"' for c in matched_num_cols)
            return f'SELECT {col_list} FROM "{best_table.table_name}" LIMIT 10'

        return None

    def synthesize_answer(
        self,
        query: str,
        prefix_blocks: List[CAGPrefixBlock],
        hits: List[Dict[str, Any]],
        sql_query: Optional[str],
        sql_rows: List[Dict[str, Any]],
        provider: str = "openai",
        custom_base_url: Optional[str] = None,
        custom_model: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Generate grounded synthesis using OpenAI, Ollama, vLLM/SGLang, or deterministic synthesis."""
        if not hits and not sql_rows:
            return (
                "ABSTAINED: No grounded evidence spans or DuckDB KAG table rows matched this query with sufficient confidence.",
                "sentinel-abstention",
            )

        context_str = "\n\n".join(b.content for b in prefix_blocks[1:])
        sql_str = ""
        if sql_query and sql_rows:
            sql_str = f"\n\nExecuted DuckDB KAG SQL:\n{sql_query}\nSQL Result Rows:\n{json.dumps(sql_rows[:15], default=str)}"

        user_prompt = (
            f"Context & Retrieved H-RAG/JEV Evidence:\n{context_str}"
            f"{sql_str}\n\n"
            f"User Question: {query}\n\n"
            "Answer concisely and accurately with inline citations like [node_id | merkle_prefix]."
        )

        # 1. Gemini Models (Google Generative AI REST API)
        if (provider in {"gemini", "default"} or not provider) and settings.gemini_api_key:
            try:
                g_model = custom_model or settings.gemini_model or "gemini-2.5-flash"
                g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": settings.gemini_api_key,
                }
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(
                        g_url,
                        headers=headers,
                        json={
                            "system_instruction": {"parts": [{"text": SYSTEM_CONSTITUTION}]},
                            "contents": [{"parts": [{"text": user_prompt}]}],
                            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 700},
                        },
                    )
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join(p.get("text", "") for p in parts).strip()
                            if text:
                                return text, f"gemini:{g_model}"
            except Exception:
                pass

        # 2. OpenAI / Compatible endpoint
        if provider in {"openai", "gemini", "default"} and settings.openai_api_key:
            try:
                from openai import OpenAI

                client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=custom_base_url or None,
                )
                chosen_model = custom_model or settings.openai_model
                resp = client.chat.completions.create(
                    model=chosen_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_CONSTITUTION},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=700,
                    temperature=0.1,
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    return text, f"openai:{chosen_model}"
            except Exception:
                pass

        # 3. Local Ollama (explicitly requested only - no silent fallback from openai, Issue #13)
        if provider in {"ollama", "local"}:
            try:
                ollama_url = (custom_base_url or settings.ollama_base_url).rstrip("/")
                ollama_model = custom_model or settings.ollama_model
                with httpx.Client(timeout=20.0) as client:
                    r = client.post(
                        f"{ollama_url}/api/chat",
                        json={
                            "model": ollama_model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_CONSTITUTION},
                                {"role": "user", "content": user_prompt},
                            ],
                            "stream": False,
                        },
                    )
                    if r.status_code == 200:
                        msg = r.json().get("message", {}).get("content", "").strip()
                        if msg:
                            return msg, f"ollama:{ollama_model}"
            except Exception:
                pass

        # 4. llama.cpp, vLLM, SGLang local endpoints
        if provider in {"vllm", "sglang", "llamacpp", "default"}:
            endpoint_map = {
                "vllm": settings.vllm_base_url or "http://127.0.0.1:8001",
                "sglang": settings.sglang_base_url or "http://127.0.0.1:30000",
                "llamacpp": settings.llamacpp_base_url or "http://127.0.0.1:8081",
                "default": settings.llamacpp_base_url or "http://127.0.0.1:8081",
            }
            target_url = (custom_base_url or endpoint_map.get(provider, "http://127.0.0.1:8081")).rstrip("/")
            target_model = custom_model or settings.vllm_model or "default"
            try:
                with httpx.Client(timeout=15.0) as client:
                    r = client.post(
                        f"{target_url}/v1/chat/completions",
                        json={
                            "model": target_model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_CONSTITUTION},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.1,
                        },
                    )
                    if r.status_code == 200:
                        msg = r.json()["choices"][0]["message"]["content"].strip()
                        if msg:
                            return msg, f"{provider}:{target_model}"
            except Exception:
                pass

        # Deterministic evidence-grounded synthesis fallback
        parts: List[str] = []
        if sql_rows:
            parts.append(f"**DuckDB KAG Deterministic Result** (`{sql_query}`): {json.dumps(sql_rows[:5], default=str)}")
        if hits:
            top = hits[0]
            parts.append(
                f"**H-RAG + JEV Grounded Evidence** [{top['node_id']} | {top['merkle_hash'][:10]}]: {top['content']}"
            )
            if len(hits) > 1:
                sec = hits[1]
                parts.append(
                    f"Supporting context [{sec['node_id']} | {sec['merkle_hash'][:10]}]: {sec['content']}"
                )
        return "\n\n".join(parts), "vortex-deterministic-synthesis"

    def inspect_ai_vault_and_providers(self) -> Dict[str, Any]:
        ollama_models: List[str] = []
        ollama_online = False
        try:
            with httpx.Client(timeout=1.5) as client:
                r = client.get(f"{settings.ollama_base_url}/api/tags")
                if r.status_code == 200:
                    ollama_online = True
                    ollama_models = [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            pass

        manifest_summary: List[str] = []
        manifest_path = settings.ai_vault_models_dir / "gdrive_manifest.json"
        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_summary = sorted({"/".join(d.get("relpath", "").split("/")[:2]) for d in data if d.get("relpath")})
            except Exception:
                pass

        active_parts: List[Dict[str, Any]] = []
        if settings.ai_vault_models_dir.exists():
            for p in settings.ai_vault_models_dir.rglob("*"):
                if p.is_file() and (p.suffix in {".safetensors", ".gguf", ".part"}):
                    active_parts.append(
                        {
                            "file": p.name,
                            "folder": p.parent.name,
                            "size_mb": round(p.stat().st_size / (1024 * 1024), 1),
                            "status": "downloading" if p.name.endswith(".part") else "ready",
                        }
                    )

        return {
            "openai_configured": bool(settings.openai_api_key),
            "openai_model": settings.openai_model,
            "ollama_online": ollama_online,
            "ollama_models": ollama_models,
            "ai_vault_dir": str(settings.ai_vault_models_dir),
            "ai_vault_manifest_families": manifest_summary,
            "ai_vault_local_artifacts": active_parts[:25],
            "vllm_configured": bool(settings.vllm_base_url),
            "sglang_configured": bool(settings.sglang_base_url),
        }
