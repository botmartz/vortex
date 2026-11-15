"""Zero-Sprawl Hybrid Storage Triad:
1. LanceDB (Arrow-backed multi-vector storage for JEV Late-Chunking spans)
2. Okapi BM25 Lexical + AST Structural Path Index
3. Embedded DuckDB 2.0 Deterministic KAG Table Store
4. Reciprocal Rank Fusion (RRF) across all retrieval modalities
"""

from __future__ import annotations

import math
import re
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyarrow as pa

from ..config import settings
from ..schemas.core import (
    ASTNode,
    ASTNodeType,
    DeterministicTableMapper,
    DocumentAST,
    DuckDBTableSchema,
    JEVChunkMetadata,
)


def _tokenize_bm25(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) >= 2]


class HybridTriadStore:
    """Manages LanceDB vector persistence, Okapi BM25 lexical scoring, DuckDB KAG tables, and RRF."""

    def __init__(self, data_dir: Optional[Path] = None, db_path: str = ":memory:") -> None:
        self._lock = threading.RLock()
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lancedb_dir = self.data_dir / "lancedb"
        self.lancedb_dir.mkdir(parents=True, exist_ok=True)

        self.documents: Dict[str, DocumentAST] = {}
        self.jev_chunks: Dict[str, JEVChunkMetadata] = {}
        self.table_mapper = DeterministicTableMapper(db_path=db_path)

        # In-memory mirrors for sub-millisecond BM25 + Cosine + RRF
        self._node_tokens: Dict[str, Counter[str]] = {}
        self._node_lengths: Dict[str, int] = {}
        self._doc_freq: Counter[str] = Counter()
        self._node_lookup: Dict[str, ASTNode] = {}
        self._lance_db: Any = None
        self._init_lancedb()

    def _init_lancedb(self) -> None:
        try:
            import lancedb  # type: ignore

            self._lance_db = lancedb.connect(str(self.lancedb_dir))
        except Exception:
            self._lance_db = None

    @property
    def lancedb_connected(self) -> bool:
        return self._lance_db is not None

    def upsert_document(
        self,
        ast: DocumentAST,
        jev_chunks: List[JEVChunkMetadata],
        tables: Optional[List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]] = None,
    ) -> None:
        with self._lock:
            # Remove previous tokens for this doc if updating
            old_doc = self.documents.get(ast.doc_id)
            if old_doc is not None:
                for old_nid in old_doc.nodes:
                    self._remove_node_bm25(old_nid)
                    self._node_lookup.pop(old_nid, None)
                    self.jev_chunks.pop(f"jev::{old_nid}", None)

            self.documents[ast.doc_id] = ast

            for nid, node in ast.nodes.items():
                if node.node_type == ASTNodeType.DOCUMENT:
                    continue
                self._node_lookup[nid] = node
                indexable = f"{' '.join(node.structural_path)} {node.title or ''} {node.content}"
                self._index_node_bm25(nid, indexable)

            for chunk in jev_chunks:
                self.jev_chunks[chunk.chunk_id] = chunk

            self._persist_lancedb_batch(jev_chunks)

            if tables:
                for schema, rows in tables:
                    self.table_mapper.register_and_ingest(schema, rows)

    def _index_node_bm25(self, node_id: str, text: str) -> None:
        tokens = _tokenize_bm25(text)
        tf = Counter(tokens)
        self._node_tokens[node_id] = tf
        self._node_lengths[node_id] = len(tokens)
        for term in tf.keys():
            self._doc_freq[term] += 1

    def _remove_node_bm25(self, node_id: str) -> None:
        old_tf = self._node_tokens.pop(node_id, None)
        self._node_lengths.pop(node_id, None)
        if old_tf:
            for term in old_tf.keys():
                self._doc_freq[term] = max(0, self._doc_freq[term] - 1)

    def _persist_lancedb_batch(self, jev_chunks: List[JEVChunkMetadata]) -> None:
        if self._lance_db is None or not jev_chunks:
            return
        try:
            dim = len(jev_chunks[0].embedding)
            if dim == 0:
                return
            table_name = f"jev_vectors_{dim}d"
            rows = []
            for c in jev_chunks:
                if len(c.embedding) != dim:
                    continue
                node = self._node_lookup.get(c.ast_node_id)
                rows.append(
                    {
                        "chunk_id": c.chunk_id,
                        "doc_id": c.doc_id,
                        "ast_node_id": c.ast_node_id,
                        "merkle_hash": c.merkle_hash,
                        "backbone_model": c.backbone_model,
                        "global_coherence_score": float(c.global_coherence_score),
                        "content": node.content if node else "",
                        "structural_path": " > ".join(node.structural_path) if node else "",
                        "vector": [float(v) for v in c.embedding],
                    }
                )
            if not rows:
                return
            schema = pa.schema(
                [
                    pa.field("chunk_id", pa.string()),
                    pa.field("doc_id", pa.string()),
                    pa.field("ast_node_id", pa.string()),
                    pa.field("merkle_hash", pa.string()),
                    pa.field("backbone_model", pa.string()),
                    pa.field("global_coherence_score", pa.float32()),
                    pa.field("content", pa.string()),
                    pa.field("structural_path", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), dim)),
                ]
            )
            pa_table = pa.Table.from_pylist(rows, schema=schema)
            if table_name in self._lance_db.list_tables().tables:
                tbl = self._lance_db.open_table(table_name)
                doc_ids = sorted({r["doc_id"] for r in rows})
                for did in doc_ids:
                    safe_did = did.replace("'", "''")
                    tbl.delete(f"doc_id = '{safe_did}'")
                tbl.add(pa_table)
            else:
                self._lance_db.create_table(table_name, data=pa_table)
        except Exception:
            # Never fail ingestion if disk table schema shifts across dimensions
            pass

    def bm25_search(self, query: str, limit: int = 12) -> List[Tuple[str, float]]:
        q_tokens = _tokenize_bm25(query)
        n_docs = len(self._node_tokens)
        if n_docs == 0 or not q_tokens:
            return []
        avgdl = sum(self._node_lengths.values()) / max(1, n_docs)
        k1 = 1.5
        b = 0.75

        scored: List[Tuple[str, float]] = []
        for nid, tf_map in self._node_tokens.items():
            dl = self._node_lengths.get(nid, 0)
            score = 0.0
            for qt in q_tokens:
                tf = tf_map.get(qt, 0)
                if tf == 0:
                    continue
                df = self._doc_freq.get(qt, 0)
                idf = math.log(((n_docs - df + 0.5) / (df + 0.5)) + 1.0)
                denom = tf + k1 * (1.0 - b + b * (dl / max(1.0, avgdl)))
                score += idf * ((tf * (k1 + 1.0)) / max(1e-9, denom))
            if score > 0.0:
                scored.append((nid, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def vector_search(self, query_vec_fn: Any, query: str, limit: int = 12) -> List[Tuple[str, float]]:
        if not self.jev_chunks:
            return []
        # Group chunks by dimension in case docs used mixed embedding providers
        by_dim: Dict[int, List[JEVChunkMetadata]] = {}
        for chunk in self.jev_chunks.values():
            if chunk.embedding:
                by_dim.setdefault(len(chunk.embedding), []).append(chunk)

        scored: List[Tuple[str, float]] = []
        for dim, chunks in by_dim.items():
            q_vec = query_vec_fn(query, target_dim=dim)
            q_norm = float(np.linalg.norm(q_vec))
            if q_norm < 1e-12:
                continue
            mat = np.array([c.embedding for c in chunks], dtype=np.float32)
            norms = np.linalg.norm(mat, axis=1)
            sims = (mat @ q_vec) / np.maximum(norms * q_norm, 1e-12)
            for chunk, sim in zip(chunks, sims.tolist()):
                if sim > 0.05:
                    scored.append((chunk.ast_node_id, float(sim)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def hybrid_rrf_search(
        self,
        query: str,
        query_vec_fn: Any,
        limit: int = 6,
        rrf_k: float = 60.0,
        ear_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            bm25_hits = self.bm25_search(query, limit=limit * 3)
            vec_hits = self.vector_search(query_vec_fn, query, limit=limit * 3)

            bm25_scores = dict(bm25_hits)
            vec_scores = dict(vec_hits)

            w_bm25 = float((ear_weights or {}).get("alpha_bm25", 1.2))
            w_vec = float((ear_weights or {}).get("beta_jev", 1.0))

            rrf_scores: Dict[str, float] = {}
            for rank, (nid, _) in enumerate(bm25_hits, start=1):
                rrf_scores[nid] = rrf_scores.get(nid, 0.0) + (w_bm25 / (rrf_k + rank))
            for rank, (nid, _) in enumerate(vec_hits, start=1):
                rrf_scores[nid] = rrf_scores.get(nid, 0.0) + (w_vec / (rrf_k + rank))

            ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
            results: List[Dict[str, Any]] = []
            for nid, rrf_val in ranked:
                node = self._node_lookup.get(nid)
                if not node:
                    continue
                chunk = self.jev_chunks.get(f"jev::{nid}")
                results.append(
                    {
                        "node_id": node.node_id,
                        "doc_id": node.doc_id,
                        "node_type": node.node_type.value,
                        "title": node.title,
                        "structural_path": node.structural_path,
                        "content": node.content,
                        "merkle_hash": node.merkle_hash or node.content_hash,
                        "bbox": node.bbox.model_dump() if node.bbox else None,
                        "bm25_score": round(bm25_scores.get(nid, 0.0), 4),
                        "jev_cosine": round(vec_scores.get(nid, 0.0), 4),
                        "global_coherence": chunk.global_coherence_score if chunk else 0.0,
                        "rrf_score": round(rrf_val, 5),
                    }
                )
            return results

    def list_duckdb_tables(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for name, schema in self.table_mapper.registry.items():
            out.append(
                {
                    "table_name": name,
                    "doc_id": schema.doc_id,
                    "source_ast_node_id": schema.source_ast_node_id,
                    "row_count": schema.row_count,
                    "columns": [c.model_dump() for c in schema.columns],
                }
            )
        return out
