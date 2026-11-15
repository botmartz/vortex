export interface HealthResponse {
  status: string;
  engine: string;
  version: string;
  kag_backend: string;
  indexed_documents: number;
  jev_chunks: number;
  duckdb_tables: number;
  smithdb?: {
    storage_backend: string;
    managed_agents: number;
    pregel_checkpoints: number;
    traces: number;
    knowledge_bases: number;
    connectors: number;
    feedback_entries: number;
  };
  cag_telemetry?: {
    total_queries: number;
    total_hits: number;
    cached_tokens_saved: number;
  };
}

export interface QueryResponse {
  verified: boolean;
  abstained: boolean;
  verdict: string;
  groundedness_score: number;
  merkle_provenance_chain: string[];
  trace_id?: string;
  frontier_harness?: {
    ear_routing?: {
      shannon_entropy: number;
      alpha_bm25: number;
      beta_jev: number;
      gamma_ast: number;
      delta_kag: number;
      strategy: string;
    };
    mcsd_speculative?: {
      drafted_tokens: number;
      accepted_tokens: number;
      total_answer_tokens: number;
      acceptance_rate_pct: number;
      estimated_speedup_x: number;
      verified_merkle_spans: number;
    };
    scg_claims?: {
      claim_count: number;
      verified_count: number;
      claims: Array<{ claim: string; status: string; backing_hash: string }>;
    };
  };
  verifai_confidence?: number;
  verifai?: {
    text: string;
    verifai_confidence: number;
    verdict: string;
    abstained: boolean;
    claims: Array<{
      statement: string;
      verdict: string;
      confidence_score: number;
      citations: Array<{
        source_id: string;
        structural_path: string[];
        merkle_hash: string;
        sha256_hash: string;
        snippet: string;
        score: number;
      }>;
      sql_expression?: string;
    }>;
    citations: Array<{
      source_id: string;
      structural_path: string[];
      merkle_hash: string;
      sha256_hash: string;
      snippet: string;
      score: number;
    }>;
    cryptographic_hashes: string[];
    sql_executed?: string;
    sql_rows: Array<Record<string, unknown>>;
  };
  result: {
    answer: string;
    synthesis_backend: string;
    kag_sql_executed?: string | null;
    kag_sql_rows: Array<Record<string, unknown>>;
    hrag_jev_hits: Array<{
      node_id: string;
      structural_path: string;
      node_type: string;
      content: string;
      merkle_hash: string;
      rrf_score: number;
    }>;
    cag_radix_telemetry?: {
      hit_rate_pct: number;
      pinned_prefix_tokens: number;
      cumulative_tokens_saved: number;
      radix_cache_hit: boolean;
    };
  };
}

export interface RagflowDuelResponse {
  query: string;
  ragflow: {
    engine: string;
    execution_ms: number;
    total_flat_chunks: number;
    top_snippet: string;
    mutation_cost: string;
    tabular_sql_capability: string;
    kv_prefix_cache: string;
    speculative_decoding: string;
    claim_verification: string;
    deployment_footprint: string;
  };
  vortex: {
    engine: string;
    execution_ms: number;
    verdict: string;
    groundedness_score: number;
    answer: string;
    ear_strategy: string;
    mcsd_speedup: string;
    scg_claims_verified: string;
    kag_sql_executed: string;
    kag_sql_rows: Array<Record<string, unknown>>;
    mutation_cost: string;
    kv_prefix_cache: string;
    deployment_footprint: string;
  };
  architecture_comparison: Array<{ feature: string; ragflow: string; vortex: string }>;
}

async function reqJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(errText || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const vortexApi = {
  getHealth: () => reqJson<HealthResponse>("/health"),

  runQuery: (payload: {
    query: string;
    provider: string;
    enable_kag_auto_sql: boolean;
    sql_override?: string | null;
  }) =>
    reqJson<QueryResponse>("/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  runRagflowDuel: (payload: { query: string; provider: string; sample_markdown?: string }) =>
    reqJson<RagflowDuelResponse>("/v1/duel/ragflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  runBenchmark: () => reqJson<Record<string, any>>("/v1/benchmark/run", { method: "POST" }),

  getAgents: () => reqJson<{ agents: Array<Record<string, any>> }>("/v1/agents"),
  upsertAgent: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),
  runAgent: (payload: {
    query: string;
    agent_id: string;
    kb_id?: string;
    enable_speculative: boolean;
    provider: string;
  }) =>
    reqJson<Record<string, any>>("/v1/agents/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  getTraces: () => reqJson<{ traces: Array<Record<string, any>>; stats: Record<string, any> }>("/v1/smithdb/traces?limit=20"),
  getCheckpoints: () => reqJson<{ checkpoints: Array<Record<string, any>> }>("/v1/smithdb/checkpoints?limit=25"),
  replayCheckpoint: (checkpoint_id: string) =>
    reqJson<Record<string, any>>("/v1/smithdb/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checkpoint_id })
    }),

  getKnowledgeBases: () => reqJson<{ knowledge_bases: Array<Record<string, any>> }>("/v1/kb"),
  createKnowledgeBase: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  ingestMarkdown: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  ingestFile: (formData: FormData) =>
    reqJson<Record<string, any>>("/v1/ingest/file", {
      method: "POST",
      body: formData
    }),

  ingestDatabase: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/ingest/db", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  getDocuments: () => reqJson<{ documents: Array<Record<string, any>> }>("/v1/documents"),
  getDocumentAst: (docId: string) => reqJson<Record<string, any>>(`/v1/documents/${encodeURIComponent(docId)}/ast`),

  getKagTables: () => reqJson<{ tables: Array<Record<string, any>> }>("/v1/kag/tables"),
  runKagSql: (sql: string) =>
    reqJson<{ sql: string; row_count: number; rows: Array<Record<string, unknown>> }>("/v1/kag/sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql })
    }),

  getConnectors: () => reqJson<{ connectors: Array<Record<string, any>> }>("/v1/connectors"),
  saveConnector: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/connectors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),
  discoverOllamaModels: (baseUrl: string) =>
    reqJson<{ online: boolean; base_url: string; models: Array<{ name: string; size_gb: number }>; error?: string }>(
      `/v1/connectors/ollama/models?base_url=${encodeURIComponent(baseUrl)}`
    ),
  getRuntimeCluster: () => reqJson<Record<string, any>>("/v1/runtime/cluster"),

  getFeedback: () => reqJson<{ feedback: Array<Record<string, any>>; count: number; average_rating: number }>("/v1/feedback"),
  submitFeedback: (payload: Record<string, any>) =>
    reqJson<Record<string, any>>("/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),

  getAgentCard: () => reqJson<Record<string, any>>("/.well-known/agent.json"),
  callA2A: (text: string) =>
    reqJson<Record<string, any>>("/a2a", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: `a2a-${Date.now()}`,
        method: "tasks/send",
        params: { message: { role: "user", parts: [{ type: "text", text }] } }
      })
    }),
  callMcp: (method: string, params: Record<string, unknown>) =>
    reqJson<Record<string, any>>("/mcp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: `mcp-${Date.now()}`, method, params })
    })
};
