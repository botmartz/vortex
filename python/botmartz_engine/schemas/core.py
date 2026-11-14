"""Core data schemas for Botmartz Omni-RAG Engine:
1. Abstract Document Tree (H-RAG / AST-based chunking + BLAKE3/SHA-256 Merkle tree diffing)
2. JEV (Joint Embedding & Late Chunking metadata)
3. KAG & Embedded DuckDB deterministic table mapper
4. CAG (Cache-Augmented Generation RadixAttention KV-cache prefix blocks)
"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple
import sqlite3
from pydantic import BaseModel, Field, computed_field


# ============================================================================
# 1. HIERARCHICAL DOCUMENT TREE (H-RAG) & MERKLE DIFFING SCHEMAS
# ============================================================================

class ASTNodeType(str, Enum):
    DOCUMENT = "document"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    LIST_ITEM = "list_item"
    EQUATION = "equation"
    FIGURE = "figure"


class BoundingBox(BaseModel):
    page: int = Field(..., ge=1, description="1-indexed page number")
    x0: float
    y0: float
    x1: float
    y1: float


class ASTNode(BaseModel):
    """Single node in the Hierarchical Document Tree (H-RAG)."""

    node_id: str = Field(..., description="Deterministic or UUID identifier for the node")
    doc_id: str = Field(..., description="Parent document identifier")
    node_type: ASTNodeType = Field(...)
    title: Optional[str] = Field(default=None, description="Heading or caption if applicable")
    content: str = Field(default="", description="Normalized textual or markdown payload")
    depth: int = Field(default=0, ge=0, description="Depth in the document hierarchy (0 = root)")
    structural_path: List[str] = Field(
        default_factory=list,
        description="Breadcrumb path from document root, e.g. ['1. Intro', '1.2 Scope']",
    )
    parent_id: Optional[str] = Field(default=None)
    children_ids: List[str] = Field(default_factory=list)
    prev_sibling_id: Optional[str] = Field(default=None)
    next_sibling_id: Optional[str] = Field(default=None)
    char_span: Tuple[int, int] = Field(
        default=(0, 0),
        description="(start_char, end_char) offset in the full document stream for JEV alignment",
    )
    bbox: Optional[BoundingBox] = Field(default=None)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    merkle_hash: Optional[str] = Field(
        default=None,
        description="Cryptographic Merkle hash incorporating content + ordered children hashes",
    )

    @computed_field
    @property
    def content_hash(self) -> str:
        """Cryptographic hash of this node's intrinsic payload (excluding children)."""
        payload = f"{self.node_type.value}|{self.title or ''}|{self.content.strip()}"
        return hashlib.blake2b(payload.encode("utf-8"), digest_size=32).hexdigest()


class MerkleChangeType(str, Enum):
    UNCHANGED = "unchanged"
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


class MerkleNodeDelta(BaseModel):
    node_id: str
    change_type: MerkleChangeType
    old_merkle_hash: Optional[str] = None
    new_merkle_hash: Optional[str] = None
    structural_path: List[str] = Field(default_factory=list)


class DocumentAST(BaseModel):
    """Complete Hierarchical Document Tree with bottom-up Merkle tree computation and diffing."""

    doc_id: str
    uri: str
    version: int = Field(default=1, ge=1)
    root_id: str
    nodes: Dict[str, ASTNode] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def compute_merkle_tree(self) -> str:
        """Compute cryptographic Merkle hashes bottom-up from leaves to `root_id`."""

        def _compute(node_id: str) -> str:
            node = self.nodes[node_id]
            child_hashes = [_compute(cid) for cid in node.children_ids if cid in self.nodes]
            hasher = hashlib.blake2b(digest_size=32)
            hasher.update(node.content_hash.encode("utf-8"))
            for ch in child_hashes:
                hasher.update(ch.encode("utf-8"))
            node.merkle_hash = hasher.hexdigest()
            return node.merkle_hash

        if self.root_id not in self.nodes:
            raise ValueError(f"Root node '{self.root_id}' not found in DocumentAST.nodes")
        return _compute(self.root_id)

    def diff(self, newer: "DocumentAST") -> List[MerkleNodeDelta]:
        """Compute surgical chunk deltas between `self` (older) and `newer` using Merkle hashes."""
        if not self.nodes[self.root_id].merkle_hash:
            self.compute_merkle_tree()
        if not newer.nodes[newer.root_id].merkle_hash:
            newer.compute_merkle_tree()

        deltas: List[MerkleNodeDelta] = []
        old_ids = set(self.nodes.keys())
        new_ids = set(newer.nodes.keys())

        for nid in sorted(new_ids - old_ids):
            n_node = newer.nodes[nid]
            deltas.append(
                MerkleNodeDelta(
                    node_id=nid,
                    change_type=MerkleChangeType.ADDED,
                    old_merkle_hash=None,
                    new_merkle_hash=n_node.merkle_hash,
                    structural_path=n_node.structural_path,
                )
            )

        for nid in sorted(old_ids - new_ids):
            o_node = self.nodes[nid]
            deltas.append(
                MerkleNodeDelta(
                    node_id=nid,
                    change_type=MerkleChangeType.DELETED,
                    old_merkle_hash=o_node.merkle_hash,
                    new_merkle_hash=None,
                    structural_path=o_node.structural_path,
                )
            )

        for nid in sorted(old_ids & new_ids):
            o_node = self.nodes[nid]
            n_node = newer.nodes[nid]
            if o_node.content_hash != n_node.content_hash:
                deltas.append(
                    MerkleNodeDelta(
                        node_id=nid,
                        change_type=MerkleChangeType.MODIFIED,
                        old_merkle_hash=o_node.merkle_hash,
                        new_merkle_hash=n_node.merkle_hash,
                        structural_path=n_node.structural_path,
                    )
                )
        return deltas


# ============================================================================
# 2. JEV (LATE CHUNKING OVER FULL DOCUMENT EMBEDDINGS) METADATA SCHEMAS
# ============================================================================

class PoolingStrategy(str, Enum):
    MEAN = "mean"
    ATTENTION_WEIGHTED = "attention_weighted"
    HIERARCHICAL_RESIDUAL = "hierarchical_residual"


class JEVChunkMetadata(BaseModel):
    """Metadata and vector carrier for JEV Late Chunking spans."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Source document ID")
    ast_node_id: str = Field(..., description="Corresponding ASTNode ID in DocumentAST")
    merkle_hash: str = Field(..., description="Merkle hash of the ASTNode at embedding time")
    backbone_model: str = Field(
        default="jinaai/jina-embeddings-v3",
        description="Long-context embedding model used for full-window token forward pass",
    )
    context_window_tokens: int = Field(default=8192, ge=128)
    doc_char_span: Tuple[int, int] = Field(..., description="(start_char, end_char) in full doc")
    doc_token_span: Tuple[int, int] = Field(..., description="(start_token, end_token) in full doc")
    pooling_strategy: PoolingStrategy = Field(default=PoolingStrategy.HIERARCHICAL_RESIDUAL)
    parent_blend_alpha: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Weight given to local late-chunked span vs parent AST node context vector",
    )
    global_coherence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Cosine similarity between late-chunked vector and full-document summary vector",
    )
    embedding: List[float] = Field(default_factory=list, description="Pooled late-chunked vector")


# ============================================================================
# 3. CAG (CACHE-AUGMENTED GENERATION) RADIX KV-CACHE SCHEMAS
# ============================================================================

class CAGPrefixBlock(BaseModel):
    """Represents a deterministic KV-cacheable prefix segment for vLLM/SGLang RadixAttention."""

    block_id: str
    tier: Literal["system", "corpus_skeleton", "pinned_ast_subtree", "session_memory"]
    merkle_hash: str
    token_count: int = Field(..., ge=0)
    content: str
    ttl_seconds: int = Field(default=3600, ge=60)


# ============================================================================
# 4. KAG & EMBEDDED DUCKDB / SQLITE DETERMINISTIC TABLE MAPPER
# ============================================================================

class DuckDBColumnSpec(BaseModel):
    name: str
    sql_type: Literal["VARCHAR", "BIGINT", "DOUBLE", "BOOLEAN", "DATE", "TIMESTAMP", "JSON"]
    nullable: bool = True
    description: Optional[str] = None


class DuckDBTableSchema(BaseModel):
    table_name: str
    doc_id: str
    source_ast_node_id: str
    columns: List[DuckDBColumnSpec]
    primary_key: List[str] = Field(default_factory=list)
    row_count: int = 0

    def to_create_table_ddl(self) -> str:
        col_defs = []
        for col in self.columns:
            null_clause = "" if col.nullable else " NOT NULL"
            col_defs.append(f'"{col.name}" {col.sql_type}{null_clause}')
        if self.primary_key:
            pk_cols = ", ".join(f'"{k}"' for k in self.primary_key)
            col_defs.append(f"PRIMARY KEY ({pk_cols})")
        cols_joined = ", ".join(col_defs)
        return f'CREATE TABLE IF NOT EXISTS "{self.table_name}" ({cols_joined});'


class DeterministicTableMapper:
    """Deterministic KAG Table Mapper with embedded DuckDB (and automatic SQLite fallback)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._backend = "sqlite3"
        try:
            import duckdb  # type: ignore

            self._conn = duckdb.connect(db_path)
            self._backend = "duckdb"
        except ImportError:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self.registry: Dict[str, DuckDBTableSchema] = {}

    @property
    def backend(self) -> str:
        return self._backend

    def register_and_ingest(
        self,
        schema: DuckDBTableSchema,
        rows: List[Dict[str, Any]],
    ) -> DuckDBTableSchema:
        """Create table deterministically and bulk-insert structured rows."""
        with self._lock:
            ddl = schema.to_create_table_ddl()
            self._conn.execute(f'DROP TABLE IF EXISTS "{schema.table_name}";')
            self._conn.execute(ddl)
            if rows:
                col_names = [c.name for c in schema.columns]
                placeholders = ", ".join(["?"] * len(col_names))
                quoted_cols = ", ".join(f'"{c}"' for c in col_names)
                insert_sql = f'INSERT INTO "{schema.table_name}" ({quoted_cols}) VALUES ({placeholders})'
                values = [[row.get(c) for c in col_names] for row in rows]
                self._conn.executemany(insert_sql, values)
                if self._backend == "sqlite3":
                    self._conn.commit()
            schema.row_count = len(rows)
            self.registry[schema.table_name] = schema
            return schema

    def execute_readonly_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a deterministic read-only analytical query for KAG synthesis."""
        normalized = sql.strip().upper()
        if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
            raise PermissionError("KAG DeterministicTableMapper only permits SELECT/WITH queries.")
        with self._lock:
            cursor = self._conn.execute(sql)
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(col_names, row)) for row in cursor.fetchall()]
