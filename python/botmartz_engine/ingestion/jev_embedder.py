"""JEV (Joint Embedding & Late Chunking) Embedder with Hierarchical Parent Residual Blending."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Dict, List, Optional

import numpy as np

from ..config import settings
from ..schemas.core import ASTNode, ASTNodeType, DocumentAST, JEVChunkMetadata, PoolingStrategy


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        return vec
    return vec / norm


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def _deterministic_semantic_projection(text: str, dims: int = 128) -> np.ndarray:
    """Fast local semantic character-ngram + token hashing projection (zero external dependency fallback)."""
    vec = np.zeros(dims, dtype=np.float32)
    cleaned = text.lower().strip()
    if not cleaned:
        return vec
    tokens = re.findall(r"[a-z0-9_]+", cleaned)
    for tok in tokens:
        h = int.from_bytes(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest(), "little")
        idx = h % dims
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log1p(len(tok)) * 0.25)
        # Character 3-grams for morphological similarity
        for i in range(max(0, len(tok) - 2)):
            tri = tok[i : i + 3]
            th = int.from_bytes(hashlib.blake2b(tri.encode("utf-8"), digest_size=4).digest(), "little")
            vec[th % dims] += 0.35 if ((th >> 3) & 1) == 0 else -0.35
    return _normalize(vec)


class JEVLateChunker:
    """Implements JEV Late Chunking + Hierarchical Parent Residual Blending."""

    def __init__(self, prefer_openai: bool = True, parent_blend_alpha: float = 0.82) -> None:
        self.prefer_openai = prefer_openai and bool(settings.openai_api_key)
        self.parent_blend_alpha = parent_blend_alpha
        self._openai_client: Optional[object] = None

    def embed_batch(self, texts: List[str]) -> tuple[List[np.ndarray], str]:
        if not texts:
            return [], "empty"

        if self.prefer_openai and settings.openai_api_key:
            try:
                from openai import OpenAI

                if self._openai_client is None:
                    self._openai_client = OpenAI(api_key=settings.openai_api_key)
                client: Any = self._openai_client  # type: ignore[name-defined]
                clipped = [t[:8000] if t.strip() else "document root" for t in texts]
                resp = client.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=clipped,
                )
                vectors = [_normalize(np.array(item.embedding, dtype=np.float32)) for item in resp.data]
                return vectors, settings.openai_embedding_model
            except Exception:
                # Fall back silently to local deterministic semantic projection
                pass

        vectors = [_deterministic_semantic_projection(t) for t in texts]
        return vectors, "vortex-local-semantic-128d"

    def embed_query(self, query: str, target_dim: Optional[int] = None) -> np.ndarray:
        if target_dim == 128:
            return _deterministic_semantic_projection(query, dims=128)
        vecs, _ = self.embed_batch([query])
        vec = vecs[0]
        if target_dim is not None and len(vec) != target_dim:
            return _deterministic_semantic_projection(query, dims=target_dim)
        return vec

    def build_jev_chunks(self, ast: DocumentAST) -> List[JEVChunkMetadata]:
        """Compute full-document global anchor + AST node spans + hierarchical parent residual blend."""
        ordered_nodes: List[ASTNode] = [
            node for node in ast.nodes.values() if node.node_type != ASTNodeType.DOCUMENT
        ]
        if not ordered_nodes:
            return []

        # Build full document summary anchor so every chunk sees global cross-chunk context
        full_doc_text = "\n".join(
            f"{' > '.join(n.structural_path)}: {n.content}" for n in ordered_nodes[:60]
        )
        span_texts = [
            f"[{' > '.join(n.structural_path)}] {n.title or ''} {n.content}".strip()
            for n in ordered_nodes
        ]
        all_texts = [full_doc_text] + span_texts
        all_vecs, backbone_name = self.embed_batch(all_texts)

        doc_global_vec = all_vecs[0]
        raw_node_vecs: Dict[str, np.ndarray] = {
            node.node_id: vec for node, vec in zip(ordered_nodes, all_vecs[1:])
        }

        # Top-down hierarchical blending: blend child span with parent's blended vector + global context
        blended_vecs: Dict[str, np.ndarray] = {}
        alpha = self.parent_blend_alpha
        for node in sorted(ordered_nodes, key=lambda n: n.depth):
            span_vec = raw_node_vecs[node.node_id]
            parent_vec = (
                blended_vecs.get(node.parent_id, doc_global_vec)
                if node.parent_id
                else doc_global_vec
            )
            combined = _normalize(alpha * span_vec + (1.0 - alpha) * (0.7 * parent_vec + 0.3 * doc_global_vec))
            blended_vecs[node.node_id] = combined

        chunks: List[JEVChunkMetadata] = []
        for node in ordered_nodes:
            vec = blended_vecs[node.node_id]
            start_c, end_c = node.char_span
            start_tok, end_tok = max(0, start_c // 4), max(1, end_c // 4)
            coherence = max(0.0, min(1.0, round((_cosine(vec, doc_global_vec) + 1.0) / 2.0, 4)))
            chunks.append(
                JEVChunkMetadata(
                    chunk_id=f"jev::{node.node_id}",
                    doc_id=ast.doc_id,
                    ast_node_id=node.node_id,
                    merkle_hash=node.merkle_hash or node.content_hash,
                    backbone_model=backbone_name,
                    context_window_tokens=32768,
                    doc_char_span=(start_c, end_c),
                    doc_token_span=(start_tok, end_tok),
                    pooling_strategy=PoolingStrategy.HIERARCHICAL_RESIDUAL,
                    parent_blend_alpha=alpha,
                    global_coherence_score=coherence,
                    embedding=[round(float(x), 6) for x in vec.tolist()],
                )
            )
        return chunks
