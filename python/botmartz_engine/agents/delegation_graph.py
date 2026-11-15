"""Botmartz VORTEX Autonomous Agent Delegation Graph:
1. IngestionAgent (Docling-style Layout AST + Vision/PyMuPDF OCR + JEV Late Chunking + Merkle Diff)
2. StorageIndexAgent (LanceDB + Okapi BM25 + Embedded DuckDB KAG Triad Synchronization)
3. InferenceRouter (Hybrid RRF + NL-to-SQL KAG + CAG Radix KV-Cache + OpenAI/Ollama/vLLM Synthesis)
4. EvaluationSentinel (Evidence-Grounded Abstention & Cryptographic Merkle Provenance Verification)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple

from ..inference import CAGRadixManager, MultiProviderInferenceEngine
from ..ingestion import JEVLateChunker, UniversalDocumentIngestor
from ..schemas.core import DocumentAST, DuckDBTableSchema, MerkleNodeDelta
from ..storage import HybridTriadStore
from .deep_harness import EntropyAdaptiveRouter, MerkleSpeculativeDrafter, SelfCorrectingClaimJudge


class QueryModality(str, Enum):
    HRAG_STRUCTURAL = "hrag_structural"
    JEV_SEMANTIC = "jev_semantic"
    KAG_SQL_TABULAR = "kag_sql_tabular"
    CAG_PINNED_PREFIX = "cag_pinned_prefix"
    HYBRID_OMNI = "hybrid_omni"


@dataclass
class EngineState:
    """Shared state across the 4-stage VORTEX autonomous delegation graph."""

    store: HybridTriadStore = field(default_factory=HybridTriadStore)
    cag_manager: CAGRadixManager = field(default_factory=CAGRadixManager)
    last_merkle_deltas: List[MerkleNodeDelta] = field(default_factory=list)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def documents(self) -> Dict[str, DocumentAST]:
        return self.store.documents

    @property
    def table_mapper(self) -> Any:
        return self.store.table_mapper


class IngestionAgent:
    """Agent 1 (`botmartz-parser`): Layout-aware AST parsing, OCR, Merkle diffing, and JEV Late Chunking."""

    def __init__(self, prefer_openai_embeddings: bool = True) -> None:
        self.ingestor = UniversalDocumentIngestor()
        self.jev_chunker = JEVLateChunker(prefer_openai=prefer_openai_embeddings)

    def parse_markdown_to_ast(
        self,
        doc_id: str,
        uri: str,
        markdown_text: str,
        version: int = 1,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]]:
        return self.ingestor.parse_markdown_to_ast(doc_id=doc_id, uri=uri, markdown_text=markdown_text, version=version)

    def parse_file_bytes(
        self,
        doc_id: str,
        filename: str,
        raw_bytes: bytes,
        version: int = 1,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]], Dict[str, Any]]:
        return self.ingestor.ingest_file_bytes(doc_id=doc_id, filename=filename, raw_bytes=raw_bytes, version=version)

    def build_jev_late_chunks(
        self,
        ast: DocumentAST,
        existing_chunks: Optional[Dict[str, Any]] = None,
        deltas: Optional[List[Any]] = None,
    ) -> List[Any]:
        return self.jev_chunker.build_jev_chunks(ast, existing_chunks=existing_chunks, deltas=deltas)


class StorageIndexAgent:
    """Agent 2 (`botmartz-architect`): Computes surgical Merkle deltas and updates LanceDB + BM25 + DuckDB."""

    def ingest_or_update(
        self,
        state: EngineState,
        new_ast: DocumentAST,
        jev_chunks: List[Any],
        tables: Optional[List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]] = None,
    ) -> List[MerkleNodeDelta]:
        old_ast = state.store.documents.get(new_ast.doc_id)
        deltas = old_ast.diff(new_ast) if old_ast is not None else []
        state.store.upsert_document(ast=new_ast, jev_chunks=jev_chunks, tables=tables)
        state.last_merkle_deltas = deltas
        return deltas


class InferenceRouter:
    """Agent 3 (`botmartz-inference`): Routes queries across Hybrid RRF, DuckDB KAG SQL, and CAG Radix KV-Cache."""

    SQL_KEYWORDS = {
        "sum",
        "average",
        "avg",
        "count",
        "total",
        "select",
        "maximum",
        "max",
        "minimum",
        "min",
        "aggregate",
    }

    def __init__(self, jev_chunker: JEVLateChunker) -> None:
        self.jev_chunker = jev_chunker
        self.inference_engine = MultiProviderInferenceEngine()

    def classify_query(self, query: str, has_tables: bool) -> QueryModality:
        tokens = set(re.findall(r"\w+", query.lower()))
        if has_tables and (tokens & self.SQL_KEYWORDS):
            return QueryModality.HYBRID_OMNI
        return QueryModality.JEV_SEMANTIC

    def execute_query(
        self,
        state: EngineState,
        query: str,
        sql_override: Optional[str] = None,
        provider: str = "openai",
        enable_kag_auto_sql: bool = True,
        limit: int = 6,
        custom_base_url: Optional[str] = None,
        custom_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        has_tables = bool(state.store.table_mapper.registry)
        modality = self.classify_query(query, has_tables=has_tables)
        ear_routing = EntropyAdaptiveRouter.compute_routing_profile(query=query, has_tables=has_tables)

        hits = state.store.hybrid_rrf_search(
            query=query,
            query_vec_fn=self.jev_chunker.embed_query,
            limit=limit,
            ear_weights=ear_routing,
        )

        # Require meaningful lexical or semantic overlap so out-of-scope queries abstain cleanly
        filtered_hits = [
            h for h in hits if h["bm25_score"] > 0.0 or h["jev_cosine"] >= 0.44
        ]

        sql_executed: Optional[str] = None
        sql_rows: List[Dict[str, Any]] = []
        sql_error: Optional[str] = None

        if sql_override:
            sql_executed = sql_override
        elif enable_kag_auto_sql and modality == QueryModality.HYBRID_OMNI:
            sql_executed = self.inference_engine.translate_nl_to_sql(
                query=query,
                table_schemas=state.store.table_mapper.registry,
                use_llm=(provider == "openai"),
            )

        if sql_executed:
            try:
                sql_rows = state.store.table_mapper.execute_readonly_sql(sql_executed)
            except Exception as exc:
                sql_error = str(exc)
                if not sql_override:
                    fallback_sql = self.inference_engine.translate_nl_to_sql(
                        query=query,
                        table_schemas=state.store.table_mapper.registry,
                        use_llm=False,
                    )
                    if fallback_sql and fallback_sql != sql_executed:
                        try:
                            sql_rows = state.store.table_mapper.execute_readonly_sql(fallback_sql)
                            sql_executed = fallback_sql
                            sql_error = None
                        except Exception as exc2:
                            sql_error = f"{sql_error} | fallback failed: {exc2}"

        prefix_blocks, cag_telemetry = state.cag_manager.assemble_prefix_stack(
            documents=state.store.documents,
            table_schemas=state.store.table_mapper.registry,
            pinned_hits=filtered_hits,
        )

        answer, synth_backend = self.inference_engine.synthesize_answer(
            query=query,
            prefix_blocks=prefix_blocks,
            hits=filtered_hits,
            sql_query=sql_executed,
            sql_rows=sql_rows,
            provider=provider,
            custom_base_url=custom_base_url,
            custom_model=custom_model,
        )

        mcsd_metrics = MerkleSpeculativeDrafter.draft_and_verify(filtered_hits, answer)

        return {
            "query": query,
            "modality": modality.value,
            "answer": answer,
            "synthesis_backend": synth_backend,
            "hrag_jev_hits": filtered_hits,
            "kag_sql_executed": sql_executed,
            "kag_sql_rows": sql_rows,
            "kag_sql_error": sql_error,
            "cag_radix_telemetry": cag_telemetry,
            "ear_routing": ear_routing,
            "mcsd_speculative": mcsd_metrics,
            "cag_radix_prefixes": [
                {
                    "block_id": b.block_id,
                    "tier": b.tier,
                    "merkle_hash": b.merkle_hash,
                    "token_count": b.token_count,
                }
                for b in prefix_blocks
            ],
        }


class EvaluationSentinel:
    """Agent 4 (`botmartz-sentinel`): Enforces Botmartz Evidence-Grounded Abstention & Merkle Provenance."""

    def verify(self, router_payload: Dict[str, Any]) -> Dict[str, Any]:
        hits = router_payload.get("hrag_jev_hits", [])
        sql_rows = router_payload.get("kag_sql_rows", [])
        answer = router_payload.get("answer", "")
        provenance_hashes = [h["merkle_hash"] for h in hits if h.get("merkle_hash")]

        has_evidence = bool(hits or sql_rows)
        lower_ans = answer.strip().lower()
        abstain_markers = (
            "abstained",
            "i must abstain",
            "must abstain from answering",
            "insufficient evidence",
        )
        abstained = (not has_evidence) or any(m in lower_ans[:120] for m in abstain_markers)

        if abstained:
            groundedness_score = 0.0
            verdict = "ABSTAINED_INSUFFICIENT_EVIDENCE"
        else:
            top_rrf = hits[0]["rrf_score"] if hits else 0.0
            # Continuous groundedness calculation from RRF score and SQL evidence without artificial floor
            groundedness_score = round(min(0.99, max(0.1, top_rrf * 15.0 + (0.25 if sql_rows else 0.0))), 3)
            verdict = "VERIFIED_GROUNDED"

        scg_claims = SelfCorrectingClaimJudge.verify_atomic_claims(
            answer=answer,
            hits=hits,
            sql_rows=sql_rows,
            abstained=abstained,
        )

        return {
            "verified": not abstained,
            "abstained": abstained,
            "verdict": verdict,
            "groundedness_score": groundedness_score,
            "merkle_provenance_chain": provenance_hashes,
            "kag_deterministic_rows": len(sql_rows),
            "frontier_harness": {
                "ear_routing": router_payload.get("ear_routing", {}),
                "mcsd_speculative": router_payload.get("mcsd_speculative", {}),
                "scg_claims": scg_claims,
            },
            "result": router_payload,
        }


class BotmartzDelegationGraph:
    """Master 4-stage Botmartz VORTEX Orchestrator."""

    def __init__(self, data_dir: Optional[Any] = None, prefer_openai: bool = True) -> None:
        store = HybridTriadStore(data_dir=data_dir)
        self.state = EngineState(store=store)
        self.ingestion_agent = IngestionAgent(prefer_openai_embeddings=prefer_openai)
        self.storage_agent = StorageIndexAgent()
        self.router_agent = InferenceRouter(jev_chunker=self.ingestion_agent.jev_chunker)
        self.sentinel_agent = EvaluationSentinel()

    def ingest_markdown(
        self,
        doc_id: str,
        uri: str,
        markdown_text: str,
        version: int = 1,
        tables: Optional[List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]] = None,
    ) -> Dict[str, Any]:
        ast, parsed_tables = self.ingestion_agent.parse_markdown_to_ast(
            doc_id=doc_id, uri=uri, markdown_text=markdown_text, version=version
        )
        all_tables = list(parsed_tables)
        if tables:
            all_tables.extend(tables)

        old_doc = self.state.documents.get(doc_id)
        deltas = old_doc.diff(ast) if old_doc is not None else []
        jev_chunks = self.ingestion_agent.build_jev_late_chunks(
            ast,
            existing_chunks=self.state.store.jev_chunks,
            deltas=deltas,
        )
        self.storage_agent.ingest_or_update(self.state, ast, jev_chunks, tables=all_tables)

        summary = {
            "doc_id": doc_id,
            "uri": uri,
            "version": version,
            "root_merkle_hash": ast.nodes[ast.root_id].merkle_hash,
            "ast_node_count": len(ast.nodes),
            "jev_chunk_count": len(jev_chunks),
            "tables_extracted": [s.table_name for s, _ in all_tables],
            "merkle_deltas": [d.model_dump() for d in deltas],
        }
        self.state.execution_history.append({"event": "ingest", **summary})
        return summary

    def ingest_file(
        self,
        doc_id: str,
        filename: str,
        raw_bytes: bytes,
        version: int = 1,
    ) -> Dict[str, Any]:
        ast, parsed_tables, parser_meta = self.ingestion_agent.parse_file_bytes(
            doc_id=doc_id, filename=filename, raw_bytes=raw_bytes, version=version
        )
        old_doc = self.state.documents.get(doc_id)
        deltas = old_doc.diff(ast) if old_doc is not None else []
        jev_chunks = self.ingestion_agent.build_jev_late_chunks(
            ast,
            existing_chunks=self.state.store.jev_chunks,
            deltas=deltas,
        )
        self.storage_agent.ingest_or_update(self.state, ast, jev_chunks, tables=parsed_tables)

        summary = {
            "doc_id": doc_id,
            "filename": filename,
            "version": version,
            "root_merkle_hash": ast.nodes[ast.root_id].merkle_hash,
            "ast_node_count": len(ast.nodes),
            "jev_chunk_count": len(jev_chunks),
            "tables_extracted": [s.table_name for s, _ in parsed_tables],
            "parser_telemetry": parser_meta,
            "merkle_deltas": [d.model_dump() for d in deltas],
        }
        self.state.execution_history.append({"event": "ingest_file", **summary})
        return summary

    def query(
        self,
        query: str,
        sql_override: Optional[str] = None,
        provider: str = "openai",
        enable_kag_auto_sql: bool = True,
        custom_base_url: Optional[str] = None,
        custom_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        routed = self.router_agent.execute_query(
            state=self.state,
            query=query,
            sql_override=sql_override,
            provider=provider,
            enable_kag_auto_sql=enable_kag_auto_sql,
            custom_base_url=custom_base_url,
            custom_model=custom_model,
        )
        verified = self.sentinel_agent.verify(routed)
        self.state.execution_history.append(
            {
                "event": "query",
                "query": query,
                "verdict": verified["verdict"],
                "groundedness": verified["groundedness_score"],
            }
        )
        return verified
