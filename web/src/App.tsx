import { useEffect, useState } from "react";
import {
  vortexApi,
  type HealthResponse,
  type QueryResponse,
  type RagflowDuelResponse
} from "./api";

type TabId =
  | "tab-console"
  | "tab-superiority"
  | "tab-agents"
  | "tab-kb-studio"
  | "tab-runtime"
  | "tab-enterprise";

type KbSubTab = "documents" | "database" | "ast" | "sql";

const TAB_HEADINGS: Record<TabId, { title: string; subtitle: string }> = {
  "tab-console": {
    title: "Omni-RAG & Frontier Harness",
    subtitle: "H-RAG AST, Entropy-Adaptive Routing, DuckDB KAG SQL, MCSD Speculative Draft, SCG Verification"
  },
  "tab-superiority": {
    title: "RAGFlow Comparison & Live Duel",
    subtitle: "Side-by-side evaluation of Infiniflow RAGFlow baseline vs. Botmartz VORTEX v0.3 architecture"
  },
  "tab-agents": {
    title: "Deep Managed Agents & SmithDB",
    subtitle: "4-superstep Pregel BSP orchestration, persistent checkpoints, waterfall traces, and time-travel replay"
  },
  "tab-kb-studio": {
    title: "Knowledge Bases & Database Ingest",
    subtitle: "Document parsing, OCR, direct SQLite/JSON database table sync, AST tree inspection, and DuckDB SQL"
  },
  "tab-runtime": {
    title: "Models, Ollama & Compute",
    subtitle: "Operator-configurable Ollama, OpenAI, vLLM, SGLang, and llama.cpp endpoints"
  },
  "tab-enterprise": {
    title: "Enterprise Scale, Protocols & Feedback",
    subtitle: "PostgreSQL & Redis scaling blueprint, developer feedback ledger, A2A and MCP endpoints"
  }
};

function DataRowsTable({ rows, emptyMessage }: { rows: Array<Record<string, unknown>>; emptyMessage: string }) {
  if (!rows || rows.length === 0) {
    return <p className="section-note">{emptyMessage}</p>;
  }
  const cols = Object.keys(rows[0]);
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx}>
              {cols.map((c) => (
                <td key={c} className="mono tabular">
                  {String(row[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("tab-console");
  const [kbSubTab, setKbSubTab] = useState<KbSubTab>("documents");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Workspace 1: Omni-RAG Console
  const [queryText, setQueryText] = useState(
    "Compare Botmartz VORTEX and Infiniflow RAGFlow on mutation cost, containers, and DuckDB KAG."
  );
  const [provider, setProvider] = useState("openai");
  const [enableKagSql, setEnableKagSql] = useState(true);
  const [sqlOverride, setSqlOverride] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryStage, setQueryStage] = useState(0);
  const [queryLatencyMs, setQueryLatencyMs] = useState<number | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [quickRating, setQuickRating] = useState("5");
  const [quickRatingNote, setQuickRatingNote] = useState("Rate this trace in SmithDB");

  // Workspace 2: RAGFlow Duel & Benchmark
  const [duelQuery, setDuelQuery] = useState(
    "Calculate total system_ram_gb across cluster nodes and compare incremental mutation cost vs RAGFlow."
  );
  const [duelProvider, setDuelProvider] = useState("openai");
  const [duelBusy, setDuelBusy] = useState(false);
  const [duelResult, setDuelResult] = useState<RagflowDuelResponse | null>(null);
  const [benchBusy, setBenchBusy] = useState(false);
  const [benchResult, setBenchResult] = useState<Record<string, any> | null>(null);

  // Workspace 3: Deep Agents & SmithDB
  const [agents, setAgents] = useState<Array<Record<string, any>>>([]);
  const [kbs, setKbs] = useState<Array<Record<string, any>>>([]);
  const [traces, setTraces] = useState<Array<Record<string, any>>>([]);
  const [checkpoints, setCheckpoints] = useState<Array<Record<string, any>>>([]);
  const [smithStats, setSmithStats] = useState<Record<string, any>>({});
  const [selectedAgentId, setSelectedAgentId] = useState("vortex-deep-supervisor");
  const [selectedKbId, setSelectedKbId] = useState("kb-enterprise-core");
  const [agentMission, setAgentMission] = useState(
    "Audit cluster telemetry in DuckDB, compare KV-cache strategies, and verify claims against Merkle hashes."
  );
  const [agentSpeculative, setAgentSpeculative] = useState(true);
  const [agentBusy, setAgentBusy] = useState(false);
  const [agentOutput, setAgentOutput] = useState("");
  const [newAgentName, setNewAgentName] = useState("");
  const [newAgentTopology, setNewAgentTopology] = useState("pregel_supervisor");
  const [newAgentRole, setNewAgentRole] = useState("Enterprise Financial & SQL Specialist");
  const [newAgentProvider, setNewAgentProvider] = useState("openai");
  const [newAgentPrompt, setNewAgentPrompt] = useState(
    "Use DuckDB KAG for exact totals, cite Merkle hashes, and abstain when evidence is absent."
  );

  // Workspace 4: KBs, Document/DB Ingest, AST & DuckDB SQL
  const [kbName, setKbName] = useState("");
  const [kbPreset, setKbPreset] = useState("hrag_jev");
  const [kbDesc, setKbDesc] = useState("");
  const [ingestDocId, setIngestDocId] = useState("enterprise_policy_doc");
  const [ingestUri, setIngestUri] = useState("vault://policies/sla.md");
  const [ingestVersion, setIngestVersion] = useState(1);
  const [ingestMarkdown, setIngestMarkdown] = useState(
    `# Enterprise Reliability Policy\n\n## Service Level Objectives\n| tier | availability_sla_pct | p95_latency_ms |\n| --- | --- | --- |\n| starter | 99.9 | 250 |\n| enterprise | 99.99 | 95 |`
  );
  const [uploadDocId, setUploadDocId] = useState("uploaded_document");
  const [uploadVersion, setUploadVersion] = useState(1);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [ingestOutput, setIngestOutput] = useState<Record<string, any> | null>(null);

  const [dbDocId, setDbDocId] = useState("quarterly_revenue_db");
  const [dbTableName, setDbTableName] = useState("q4_region_revenue");
  const [dbSourceType, setDbSourceType] = useState("inline_table");
  const [dbKbId, setDbKbId] = useState("kb-financial-olap");
  const [dbSqlitePath, setDbSqlitePath] = useState("");
  const [dbSqliteQuery, setDbSqliteQuery] = useState("SELECT * FROM managed_agents LIMIT 50");
  const [dbInlineJson, setDbInlineJson] = useState(
    `[\n  {"region": "North America", "arr_usd": 420000, "active_tenants": 38, "retention_pct": 97.4},\n  {"region": "Europe", "arr_usd": 295000, "active_tenants": 29, "retention_pct": 96.1},\n  {"region": "APAC", "arr_usd": 360000, "active_tenants": 44, "retention_pct": 98.2}\n]`
  );
  const [dbSyncStatus, setDbSyncStatus] = useState("");

  const [documents, setDocuments] = useState<Array<Record<string, any>>>([]);
  const [selectedAstDoc, setSelectedAstDoc] = useState("");
  const [astPayload, setAstPayload] = useState<Record<string, any> | null>(null);
  const [kagTables, setKagTables] = useState<Array<Record<string, any>>>([]);
  const [kagSql, setKagSql] = useState("");
  const [kagSqlOutput, setKagSqlOutput] = useState<{ rows: Array<Record<string, unknown>>; note: string }>({
    rows: [],
    note: "Select a table or execute a read-only SQL query."
  });

  // Workspace 5: Connectors & Compute
  const [connectors, setConnectors] = useState<Array<Record<string, any>>>([]);
  const [connProvider, setConnProvider] = useState("ollama");
  const [connName, setConnName] = useState("Primary Ollama Endpoint");
  const [connUrl, setConnUrl] = useState("http://localhost:11434");
  const [connModel, setConnModel] = useState("gpt-oss:120b-cloud");
  const [ollamaDiscovery, setOllamaDiscovery] = useState<{
    online: boolean;
    base_url: string;
    models: Array<{ name: string; size_gb: number }>;
    error?: string;
  } | null>(null);
  const [runtimeCluster, setRuntimeCluster] = useState<Record<string, any> | null>(null);

  // Workspace 6: Enterprise Feedback, A2A & MCP
  const [feedbackList, setFeedbackList] = useState<Array<Record<string, any>>>([]);
  const [feedbackStats, setFeedbackStats] = useState({ count: 0, average_rating: 0 });
  const [fbReviewer, setFbReviewer] = useState("Lead Architect");
  const [fbOrg, setFbOrg] = useState("Beta Partner");
  const [fbRating, setFbRating] = useState("5");
  const [fbComment, setFbComment] = useState("");
  const [agentCardText, setAgentCardText] = useState("");
  const [a2aInput, setA2aInput] = useState("Verify DuckDB KAG cluster row counts via A2A.");
  const [a2aOutput, setA2aOutput] = useState("");
  const [mcpOutput, setMcpOutput] = useState("");

  async function refreshHealth() {
    try {
      const h = await vortexApi.getHealth();
      setHealth(h);
    } catch {
      // Keep previous health state if transient network error
    }
  }

  useEffect(() => {
    refreshHealth();
    const timer = window.setInterval(refreshHealth, 12000);
    return () => window.clearInterval(timer);
  }, []);

  async function refreshAgentsPanel() {
    const [agRes, trRes, cpRes, kbRes] = await Promise.all([
      vortexApi.getAgents(),
      vortexApi.getTraces(),
      vortexApi.getCheckpoints(),
      vortexApi.getKnowledgeBases()
    ]);
    setAgents(agRes.agents || []);
    setTraces(trRes.traces || []);
    setSmithStats(trRes.stats || {});
    setCheckpoints(cpRes.checkpoints || []);
    setKbs(kbRes.knowledge_bases || []);
  }

  async function refreshKbAndDocs(sub?: KbSubTab) {
    const [kbRes, docRes, tblRes] = await Promise.all([
      vortexApi.getKnowledgeBases(),
      vortexApi.getDocuments(),
      vortexApi.getKagTables()
    ]);
    setKbs(kbRes.knowledge_bases || []);
    const docs = docRes.documents || [];
    setDocuments(docs);
    setKagTables(tblRes.tables || []);
    if (docs.length > 0 && (!selectedAstDoc || sub === "ast")) {
      const target = selectedAstDoc || docs[0].doc_id;
      setSelectedAstDoc(target);
      const astData = await vortexApi.getDocumentAst(target);
      setAstPayload(astData);
    }
  }

  async function refreshRuntimePanel() {
    const [connRes, rtRes] = await Promise.all([vortexApi.getConnectors(), vortexApi.getRuntimeCluster()]);
    setConnectors(connRes.connectors || []);
    setRuntimeCluster(rtRes);
  }

  async function refreshEnterprisePanel() {
    const [fbRes, card] = await Promise.all([vortexApi.getFeedback(), vortexApi.getAgentCard()]);
    setFeedbackList(fbRes.feedback || []);
    setFeedbackStats({ count: fbRes.count, average_rating: fbRes.average_rating });
    setAgentCardText(JSON.stringify(card, null, 2));
  }

  function handleTabChange(tab: TabId) {
    setActiveTab(tab);
    if (tab === "tab-agents") void refreshAgentsPanel();
    if (tab === "tab-kb-studio") void refreshKbAndDocs();
    if (tab === "tab-runtime") void refreshRuntimePanel();
    if (tab === "tab-enterprise") void refreshEnterprisePanel();
  }

  async function handleRunQuery() {
    if (!queryText.trim()) return;
    setQueryBusy(true);
    setQueryStage(2);
    const t0 = performance.now();
    try {
      const res = await vortexApi.runQuery({
        query: queryText.trim(),
        provider,
        enable_kag_auto_sql: enableKagSql,
        sql_override: sqlOverride.trim() || null
      });
      setQueryLatencyMs(Math.round(performance.now() - t0));
      setQueryResult(res);
      setQueryStage(5);
      setQuickRatingNote("Rate this trace in SmithDB");
      void refreshHealth();
    } finally {
      setQueryBusy(false);
    }
  }

  async function handleSaveQuickRating() {
    await vortexApi.submitFeedback({
      trace_id: queryResult?.trace_id ?? null,
      reviewer: "Console Evaluator",
      rating: Number(quickRating),
      category: "trace_eval",
      comment: `Console evaluation rating for trace ${queryResult?.trace_id ?? "live"}`
    });
    setQuickRatingNote("Rating persisted to SmithDB.");
    void refreshHealth();
  }

  async function handleRunDuel() {
    if (!duelQuery.trim()) return;
    setDuelBusy(true);
    try {
      const res = await vortexApi.runRagflowDuel({
        query: duelQuery.trim(),
        provider: duelProvider
      });
      setDuelResult(res);
      void refreshHealth();
    } finally {
      setDuelBusy(false);
    }
  }

  async function handleRunBenchmark() {
    setBenchBusy(true);
    try {
      const res = await vortexApi.runBenchmark();
      setBenchResult(res);
    } finally {
      setBenchBusy(false);
    }
  }

  async function handleRunAgent() {
    setAgentBusy(true);
    try {
      const res = await vortexApi.runAgent({
        query: agentMission.trim(),
        agent_id: selectedAgentId,
        kb_id: selectedKbId,
        enable_speculative: agentSpeculative,
        provider
      });
      setAgentOutput(
        `Trace ${res.trace_id} | Thread ${res.thread_id} | ${res.total_latency_ms} ms\n` +
          `Verdict: ${res.verdict} (Groundedness ${res.groundedness_score})\n` +
          `MCSD Speculative Speedup: ${res.mcsd_speculative?.estimated_speedup_x ?? 1}x | SCG Verified: ${res.scg_claims?.verified_count ?? 0}/${res.scg_claims?.claim_count ?? 0}\n\n` +
          `${res.answer ?? ""}`
      );
      await refreshAgentsPanel();
      void refreshHealth();
    } finally {
      setAgentBusy(false);
    }
  }

  async function handleCreateAgent() {
    if (!newAgentName.trim()) return;
    await vortexApi.upsertAgent({
      name: newAgentName.trim(),
      role: newAgentRole.trim(),
      topology: newAgentTopology,
      provider: newAgentProvider,
      system_prompt: newAgentPrompt.trim()
    });
    setNewAgentName("");
    await refreshAgentsPanel();
  }

  async function handleReplayCheckpoint(cpId: string) {
    const res = await vortexApi.replayCheckpoint(cpId);
    setAgentOutput(
      `Time-Travel Replay from ${cpId} -> Thread ${res.thread_id}\nVerdict: ${res.verdict}\n\n${res.answer ?? ""}`
    );
    await refreshAgentsPanel();
  }

  async function handleCreateKb() {
    if (!kbName.trim()) return;
    await vortexApi.createKnowledgeBase({
      name: kbName.trim(),
      chunk_preset: kbPreset,
      description: kbDesc.trim()
    });
    setKbName("");
    setKbDesc("");
    await refreshKbAndDocs();
  }

  async function handleIngestMarkdown() {
    const res = await vortexApi.ingestMarkdown({
      doc_id: ingestDocId.trim(),
      uri: ingestUri.trim(),
      version: ingestVersion,
      markdown_text: ingestMarkdown
    });
    setIngestOutput(res);
    void refreshHealth();
    void refreshKbAndDocs();
  }

  async function handleUploadFile() {
    if (!uploadFile) return;
    const fd = new FormData();
    fd.append("doc_id", uploadDocId.trim() || "uploaded_doc");
    fd.append("version", String(uploadVersion));
    fd.append("file", uploadFile);
    const res = await vortexApi.ingestFile(fd);
    setIngestOutput(res);
    void refreshHealth();
    void refreshKbAndDocs();
  }

  async function handleSyncDatabase() {
    try {
      const payload: Record<string, any> = {
        doc_id: dbDocId.trim(),
        table_name: dbTableName.trim(),
        kb_id: dbKbId.trim(),
        source_type: dbSourceType
      };
      if (dbSourceType === "sqlite") {
        payload.sqlite_path = dbSqlitePath.trim();
        payload.query = dbSqliteQuery.trim();
      } else {
        payload.rows = JSON.parse(dbInlineJson);
      }
      const res = await vortexApi.ingestDatabase(payload);
      setDbSyncStatus(
        `Synced ${res.imported_rows} rows into DuckDB tables: ${(res.tables_extracted || []).join(", ")}`
      );
      void refreshHealth();
      void refreshKbAndDocs();
    } catch (err) {
      setDbSyncStatus(`Sync failed: ${String(err)}`);
    }
  }

  async function handleSaveConnector() {
    await vortexApi.saveConnector({
      connector_id: `${connProvider}-custom`,
      name: connName.trim(),
      provider_type: connProvider,
      base_url: connUrl.trim(),
      model_name: connModel.trim(),
      enabled: true
    });
    await refreshRuntimePanel();
  }

  async function handleDiscoverOllama() {
    const res = await vortexApi.discoverOllamaModels(connUrl.trim());
    setOllamaDiscovery(res);
  }

  async function handleSubmitFeedback() {
    if (!fbComment.trim()) return;
    await vortexApi.submitFeedback({
      reviewer: fbReviewer.trim(),
      organization: fbOrg.trim(),
      rating: Number(fbRating),
      category: "enterprise_eval",
      comment: fbComment.trim()
    });
    setFbComment("");
    await refreshEnterprisePanel();
  }

  const cagHitRate = health?.cag_telemetry?.total_queries
    ? Math.round((health.cag_telemetry.total_hits / health.cag_telemetry.total_queries) * 100)
    : 0;
  const benchMetrics = benchResult?.measured_metrics;

  return (
    <div className="editorial-shell">
      {/* LEFT EDITORIAL NAVIGATION RAIL */}
      <aside className="rail">
        <div>
          <div className="brand-lockup">
            <div className="brand-overline">Botmartz AI Systems</div>
            <div className="brand-name">VORTEX Studio</div>
          </div>

          <div className="nav-section">
            <div className="nav-section-label">Evaluation</div>
            <button
              type="button"
              className={`nav-item ${activeTab === "tab-console" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-console")}
            >
              <span>Omni-RAG &amp; Harness</span>
            </button>
            <button
              id="tab-superiority"
              type="button"
              className={`nav-item ${activeTab === "tab-superiority" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-superiority")}
            >
              <span>RAGFlow Live Duel</span>
              <span className="nav-count">A/B</span>
            </button>
          </div>

          <div className="nav-section">
            <div className="nav-section-label">Agents &amp; Knowledge</div>
            <button
              id="tab-agents"
              type="button"
              className={`nav-item ${activeTab === "tab-agents" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-agents")}
            >
              <span>Deep Agents &amp; SmithDB</span>
              <span className="nav-count">{health?.smithdb?.traces ?? 0}</span>
            </button>
            <button
              type="button"
              className={`nav-item ${activeTab === "tab-kb-studio" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-kb-studio")}
            >
              <span>Knowledge &amp; DB Ingest</span>
              <span className="nav-count">{health?.indexed_documents ?? 0}</span>
            </button>
          </div>

          <div className="nav-section">
            <div className="nav-section-label">Operations</div>
            <button
              id="tab-runtime"
              type="button"
              className={`nav-item ${activeTab === "tab-runtime" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-runtime")}
            >
              <span>Models, Ollama &amp; Compute</span>
            </button>
            <button
              type="button"
              className={`nav-item ${activeTab === "tab-enterprise" ? "active" : ""}`}
              onClick={() => handleTabChange("tab-enterprise")}
            >
              <span>Enterprise &amp; Feedback</span>
            </button>
          </div>
        </div>

        <div className="rail-footnote">
          <div className="rail-meta-row">
            <span>SmithDB Store</span>
            <span className="mono">{health?.smithdb?.managed_agents ?? 4} agents</span>
          </div>
          <div className="rail-meta-row">
            <span>Harness Algorithms</span>
            <span className="mono">EAR / MCSD / SCG</span>
          </div>
          <div className="rail-meta-row">
            <span>Architecture</span>
            <span className="mono">Zero-Sprawl v{health?.version ?? "0.3.0"}</span>
          </div>
        </div>
      </aside>

      {/* MAIN PAPER WORKSPACE */}
      <div className="workspace-sheet">
        <header className="topbar">
          <div>
            <div className="topbar-title">{TAB_HEADINGS[activeTab].title}</div>
            <div className="topbar-sub">{TAB_HEADINGS[activeTab].subtitle}</div>
          </div>
          <div className="topbar-metrics tabular">
            <span className="inline-stat">
              <span className="status-dot" />
              <strong>v{health?.version ?? "0.3.0"}</strong>
            </span>
            <span className="inline-stat">
              Docs <strong>{health?.indexed_documents ?? 0}</strong>
            </span>
            <span className="inline-stat">
              Tables <strong>{health?.duckdb_tables ?? 0}</strong>
            </span>
            <span className="inline-stat">
              CAG Reuse <strong>{cagHitRate}%</strong>
            </span>
            <button
              type="button"
              className="btn btn-sm btn-terracotta"
              onClick={() => {
                handleTabChange("tab-superiority");
                void handleRunDuel();
              }}
            >
              Run RAGFlow Duel
            </button>
          </div>
        </header>

        <main className="sheet-body">
          {/* ============================================================== */}
          {/* TAB 1: OMNI-RAG & FRONTIER HARNESS                              */}
          {/* ============================================================== */}
          {activeTab === "tab-console" && (
            <div>
              <div className="pipeline-line">
                {[
                  { idx: 1, title: "AST & OCR Parse", desc: "BLAKE3 subtree tree" },
                  { idx: 2, title: "EAR + JEV RRF", desc: "Entropy-tuned fusion" },
                  { idx: 3, title: "DuckDB KAG SQL", desc: "Deterministic math" },
                  { idx: 4, title: "MCSD + CAG KV", desc: "Speculative draft" },
                  { idx: 5, title: "SCG Auditor", desc: "Claim gate" }
                ].map((s) => (
                  <div
                    key={s.idx}
                    className={`pipeline-step ${queryBusy && s.idx === 2 ? "running" : queryStage >= s.idx ? "done" : ""}`}
                  >
                    <div className="pipeline-step-num">0{s.idx}</div>
                    <div className="pipeline-step-title">{s.title}</div>
                    <div className="pipeline-step-desc">{s.desc}</div>
                  </div>
                ))}
              </div>

              <div className="split-columns">
                <div>
                  <div className="section-block">
                    <div className="section-heading">
                      <span className="section-title">Query Composer</span>
                      <span className="section-note">
                        {queryLatencyMs !== null ? `Completed in ${queryLatencyMs} ms` : "Auto-recorded in SmithDB"}
                      </span>
                    </div>

                    <div className="text-link-row">
                      <button
                        type="button"
                        className="text-action"
                        onClick={() =>
                          setQueryText(
                            "Compare Botmartz VORTEX and Infiniflow RAGFlow on mutation cost, containers, and DuckDB KAG."
                          )
                        }
                      >
                        Compare VORTEX vs. RAGFlow
                      </button>
                      <button
                        type="button"
                        className="text-action"
                        onClick={() =>
                          setQueryText(
                            "Calculate total and average system_ram_gb and gpu_vram_gb across the cluster telemetry table."
                          )
                        }
                      >
                        Deterministic DuckDB Math
                      </button>
                      <button
                        type="button"
                        className="text-action"
                        onClick={() =>
                          setQueryText("What is the secret Mars quantum banana launch code from 2099?")
                        }
                      >
                        Test Hard Abstention
                      </button>
                    </div>

                    <textarea rows={3} value={queryText} onChange={(e) => setQueryText(e.target.value)} />

                    <div className="form-grid-2" style={{ marginTop: 12 }}>
                      <div>
                        <label className="field-label" htmlFor="provider-select">Model Provider</label>
                        <select id="provider-select" value={provider} onChange={(e) => setProvider(e.target.value)}>
                          <option value="gemini">Gemini (Google AI Primary)</option>
                          <option value="ollama">Ollama (Local / Cloud)</option>
                          <option value="llamacpp">llama.cpp Server</option>
                          <option value="openai">OpenAI / Compatible</option>
                          <option value="sglang">SGLang RadixAttention</option>
                          <option value="vllm">vLLM PagedAttention + APC</option>
                        </select>
                      </div>
                      <div>
                        <label className="field-label" htmlFor="sql-override">Optional SQL Override</label>
                        <input
                          id="sql-override"
                          type="text"
                          className="mono"
                          placeholder="Auto-SQL when blank"
                          value={sqlOverride}
                          onChange={(e) => setSqlOverride(e.target.value)}
                        />
                      </div>
                    </div>

                    <div
                      style={{
                        marginTop: 14,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12
                      }}
                    >
                      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={enableKagSql}
                          onChange={(e) => setEnableKagSql(e.target.checked)}
                          style={{ accentColor: "#141413" }}
                        />
                        Enable DuckDB KAG Auto-SQL
                      </label>
                      <button type="button" className="btn btn-primary" disabled={queryBusy} onClick={handleRunQuery}>
                        {queryBusy ? "Executing..." : "Run Omni-RAG Query"}
                      </button>
                    </div>
                  </div>

                  <div className="section-block">
                    <div className="section-heading">
                      <span className="section-title">Sentinel Response</span>
                      <div style={{ display: "flex", gap: 8 }}>
                        <span className={`pill ${queryResult?.abstained ? "pill-ochre" : "pill-sage"}`}>
                          {queryResult?.verdict ?? "AWAITING QUERY"}
                        </span>
                        <span className="pill pill-stone">{queryResult?.result.synthesis_backend ?? "-"}</span>
                      </div>
                    </div>

                    <div className="answer-prose">
                      {queryResult?.result.answer ??
                        "Run a query to inspect Entropy-Adaptive Routing (EAR), exact DuckDB SQL execution, Merkle-Conditioned Speculative Drafting (MCSD), and Self-Correcting Claim verification (SCG)."}
                    </div>

                    <div
                      style={{
                        paddingTop: 10,
                        borderTop: "1px solid var(--border-hairline)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: 10
                      }}
                    >
                      <span className="section-note">{quickRatingNote}</span>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <select
                          value={quickRating}
                          onChange={(e) => setQuickRating(e.target.value)}
                          style={{ width: "auto", padding: "5px 9px", fontSize: 12 }}
                        >
                          <option value="5">5 / 5 - Production Ready</option>
                          <option value="4">4 / 5 - Strong</option>
                          <option value="3">3 / 5 - Needs Tuning</option>
                          <option value="2">2 / 5 - Weak</option>
                          <option value="1">1 / 5 - Failed</option>
                        </select>
                        <button type="button" className="btn btn-sm" onClick={handleSaveQuickRating}>
                          Save Rating
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="col-divided">
                  <div className="section-block">
                    <div className="section-heading">
                      <span className="section-title">Harness Telemetry</span>
                      <span className="pill pill-terracotta">
                        {queryResult?.frontier_harness?.ear_routing?.strategy ?? "standby"}
                      </span>
                    </div>

                    <div className="metric-strip" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                      <div className="metric-cell">
                        <div className="metric-label">EAR Entropy H(q)</div>
                        <div className="metric-val tabular">
                          {queryResult?.frontier_harness?.ear_routing?.shannon_entropy ?? "--"}
                        </div>
                        <div className="metric-sub mono">
                          B:{queryResult?.frontier_harness?.ear_routing?.alpha_bm25 ?? 0} K:
                          {queryResult?.frontier_harness?.ear_routing?.delta_kag ?? 0}
                        </div>
                      </div>
                      <div className="metric-cell" style={{ borderRight: "none", marginRight: 0 }}>
                        <div className="metric-label">MCSD Speculative</div>
                        <div className="metric-val tabular">
                          {queryResult?.frontier_harness?.mcsd_speculative?.estimated_speedup_x ?? "1.0"}x
                        </div>
                        <div className="metric-sub">
                          {queryResult?.frontier_harness?.mcsd_speculative?.acceptance_rate_pct ?? 0}% Merkle n-gram
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {(queryResult?.frontier_harness?.scg_claims?.claims || []).map((c, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 10,
                            padding: "6px 0",
                            borderBottom: "1px solid var(--border-hairline)",
                            fontSize: 12
                          }}
                        >
                          <span style={{ color: "var(--ink-secondary)" }}>{c.claim}</span>
                          <span className={`pill ${c.status === "ABSTAINED" ? "pill-ochre" : "pill-sage"}`}>
                            {c.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="section-block">
                    <div className="section-heading">
                      <span className="section-title">DuckDB KAG SQL</span>
                      <span className="section-note">{queryResult?.result.kag_sql_rows.length ?? 0} rows</span>
                    </div>
                    <div className="code-line" style={{ marginBottom: 12 }}>
                      {queryResult?.result.kag_sql_executed || "No SQL statement executed."}
                    </div>
                    <DataRowsTable rows={queryResult?.result.kag_sql_rows || []} emptyMessage="No SQL rows returned." />
                  </div>

                  <div>
                    <div className="section-heading">
                      <span className="section-title">Merkle Provenance</span>
                      <span className="section-note">{queryResult?.merkle_provenance_chain.length ?? 0} hashes</span>
                    </div>
                    {(queryResult?.result.hrag_jev_hits || []).map((h) => (
                      <div key={h.node_id} className="evidence-entry">
                        <div style={{ fontSize: 11.5, color: "var(--accent-terracotta)", fontWeight: 600 }}>
                          {h.structural_path} <span className="mono">#{h.merkle_hash.slice(0, 10)}</span>
                        </div>
                        <div style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginTop: 3 }}>
                          {h.content.slice(0, 210)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 2: RAGFLOW SIDE-BY-SIDE DUEL & STRESS BENCHMARK            */}
          {/* ============================================================== */}
          {activeTab === "tab-superiority" && (
            <div>
              <div className="section-block">
                <div className="form-grid-3" style={{ alignItems: "end" }}>
                  <div style={{ gridColumn: "span 2" }}>
                    <label className="field-label" htmlFor="duel-query">Side-by-Side Comparison Query</label>
                    <input
                      id="duel-query"
                      type="text"
                      value={duelQuery}
                      onChange={(e) => setDuelQuery(e.target.value)}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <select value={duelProvider} onChange={(e) => setDuelProvider(e.target.value)}>
                      <option value="openai">openai</option>
                      <option value="ollama">ollama</option>
                      <option value="sglang">sglang</option>
                      <option value="vllm">vllm</option>
                    </select>
                    <button type="button" className="btn btn-primary" disabled={duelBusy} onClick={handleRunDuel}>
                      {duelBusy ? "Running..." : "Execute Duel"}
                    </button>
                  </div>
                </div>
              </div>

              {duelResult && (
                <div className="section-block">
                  <div className="split-equal">
                    <div>
                      <div className="section-heading">
                        <span className="section-title">Infiniflow RAGFlow Baseline</span>
                        <span className="pill pill-ochre tabular">{duelResult.ragflow.execution_ms} ms</span>
                      </div>
                      <p style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginBottom: 8 }}>
                        <strong>Flat Chunks:</strong> {duelResult.ragflow.total_flat_chunks} &middot;{" "}
                        <strong>Mutation:</strong> {duelResult.ragflow.mutation_cost}
                      </p>
                      <p style={{ fontSize: 12.5, color: "var(--status-ochre)", marginBottom: 8 }}>
                        <strong>Tabular Math:</strong> {duelResult.ragflow.tabular_sql_capability}
                      </p>
                      <p style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginBottom: 10 }}>
                        <strong>Footprint:</strong> {duelResult.ragflow.deployment_footprint}
                      </p>
                      <div className="answer-prose">{duelResult.ragflow.top_snippet}</div>
                    </div>

                    <div className="col-divided">
                      <div className="section-heading">
                        <span className="section-title">Botmartz VORTEX v0.3</span>
                        <span className="pill pill-sage tabular">{duelResult.vortex.execution_ms} ms</span>
                      </div>
                      <p style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginBottom: 8 }}>
                        <strong>Verdict:</strong> {duelResult.vortex.verdict} ({duelResult.vortex.groundedness_score}) &middot;{" "}
                        <strong>SCG Claims:</strong> {duelResult.vortex.scg_claims_verified}
                      </p>
                      <p style={{ fontSize: 12.5, color: "var(--status-sage)", marginBottom: 8 }}>
                        <strong>Mutation:</strong> {duelResult.vortex.mutation_cost} &middot;{" "}
                        <strong>MCSD:</strong> {duelResult.vortex.mcsd_speedup}
                      </p>
                      <p style={{ fontSize: 12.5, color: "var(--ink-secondary)", marginBottom: 10 }}>
                        <strong>DuckDB SQL:</strong> <span className="mono">{duelResult.vortex.kag_sql_executed}</span> (
                        {duelResult.vortex.kag_sql_rows.length} rows)
                      </p>
                      <div className="answer-prose">{duelResult.vortex.answer}</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="section-block">
                <div className="section-heading">
                  <span className="section-title">Module-by-Module Architectural Matrix</span>
                  <span className="section-note">Infiniflow RAGFlow Internal vs. Botmartz VORTEX</span>
                </div>
                <div className="data-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Capability</th>
                        <th>Infiniflow RAGFlow</th>
                        <th className="vortex-col">Botmartz VORTEX v0.3</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        duelResult?.architecture_comparison || [
                          { feature: "Agent Orchestration", ragflow: "internal/harness Go Pregel + ES/MySQL stack", vortex: "Pregel BSP Harness + SmithDB + A2A + MCP" },
                          { feature: "Document Parsing", ragflow: "DeepDoc layout + fixed token chunks", vortex: "Docling/PyMuPDF + RapidOCR + H-RAG AST + JEV" },
                          { feature: "Mutation Complexity", ragflow: "O(N) full document re-index", vortex: "O(Delta) BLAKE3 Merkle diff (~90%+ skipped)" },
                          { feature: "Tabular Math", ragflow: "Markdown/HTML text approximation", vortex: "Embedded DuckDB 2.0 deterministic OLAP SQL" },
                          { feature: "KV Cache & Drafting", ragflow: "None (stateless)", vortex: "SGLang Radix / vLLM APC + MCSD lookup draft" }
                        ]
                      ).map((row) => (
                        <tr key={row.feature}>
                          <td><strong>{row.feature}</strong></td>
                          <td>{row.ragflow}</td>
                          <td className="vortex-col">{row.vortex}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <div className="section-heading">
                  <span className="section-title">4-Stage Latency Stress Benchmark</span>
                  <button type="button" className="btn btn-sm" disabled={benchBusy} onClick={handleRunBenchmark}>
                    {benchBusy ? "Running..." : "Run Stress Benchmark"}
                  </button>
                </div>
                <div className="metric-strip tabular">
                  <div className="metric-cell">
                    <div className="metric-label">AST + BLAKE3 Build</div>
                    <div className="metric-val">{benchMetrics?.ast_build_ms ?? "--"} ms</div>
                    <div className="metric-sub">{benchMetrics?.total_ast_nodes ?? 0} nodes parsed</div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Merkle Diff Cost</div>
                    <div className="metric-val">{benchMetrics?.merkle_diff_ms ?? "--"} ms</div>
                    <div className="metric-sub">{benchMetrics?.nodes_skipped_pct ?? 0}% skipped</div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">Hybrid RRF Mean</div>
                    <div className="metric-val">{benchMetrics?.hybrid_rrf_ms ?? "--"} ms</div>
                    <div className="metric-sub">5-query fusion average</div>
                  </div>
                  <div className="metric-cell">
                    <div className="metric-label">DuckDB KAG Mean</div>
                    <div className="metric-val">{benchMetrics?.duckdb_kag_ms ?? "--"} ms</div>
                    <div className="metric-sub">{benchMetrics?.duckdb_rows_checked ?? 0} rows verified</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 3: DEEP MANAGED AGENTS & SMITHDB                           */}
          {/* ============================================================== */}
          {activeTab === "tab-agents" && (
            <div>
              <div className="metric-strip tabular">
                <div className="metric-cell">
                  <div className="metric-label">Managed Agents</div>
                  <div className="metric-val">{smithStats.managed_agents ?? agents.length}</div>
                  <div className="metric-sub">SmithDB Registry</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Pregel Checkpoints</div>
                  <div className="metric-val">{smithStats.pregel_checkpoints ?? checkpoints.length}</div>
                  <div className="metric-sub">Superstep snapshots</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Recorded Traces</div>
                  <div className="metric-val">{smithStats.traces ?? traces.length}</div>
                  <div className="metric-sub">Waterfall spans</div>
                </div>
                <div className="metric-cell">
                  <div className="metric-label">Persistence Layer</div>
                  <div className="metric-val" style={{ fontSize: 18 }}>SQLite WAL</div>
                  <div className="metric-sub">PostgreSQL-ready schema</div>
                </div>
              </div>

              <div className="split-equal section-block">
                <div>
                  <div className="section-heading">
                    <span className="section-title">Run 4-Superstep Pregel Agent</span>
                  </div>
                  <div className="form-grid-2" style={{ marginBottom: 10 }}>
                    <div>
                      <label className="field-label">Agent</label>
                      <select value={selectedAgentId} onChange={(e) => setSelectedAgentId(e.target.value)}>
                        {agents.map((a) => (
                          <option key={a.agent_id} value={a.agent_id}>
                            {a.name} ({a.topology})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="field-label">Knowledge Base</label>
                      <select value={selectedKbId} onChange={(e) => setSelectedKbId(e.target.value)}>
                        {kbs.map((k) => (
                          <option key={k.kb_id} value={k.kb_id}>
                            {k.name} [{k.chunk_preset}]
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <textarea rows={3} value={agentMission} onChange={(e) => setAgentMission(e.target.value)} />
                  <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5 }}>
                      <input
                        type="checkbox"
                        checked={agentSpeculative}
                        onChange={(e) => setAgentSpeculative(e.target.checked)}
                      />
                      Enable MCSD Speculative Lookup
                    </label>
                    <button type="button" className="btn btn-primary" disabled={agentBusy} onClick={handleRunAgent}>
                      {agentBusy ? "Executing..." : "Run Deep Agent"}
                    </button>
                  </div>
                  <div className="answer-prose" style={{ marginTop: 12 }}>
                    {agentOutput || "Launch a Pregel superstep workflow to record checkpoints and trace spans."}
                  </div>
                </div>

                <div className="col-divided">
                  <div className="section-heading">
                    <span className="section-title">Register Managed Agent</span>
                  </div>
                  <div className="form-grid-2" style={{ marginBottom: 10 }}>
                    <div>
                      <label className="field-label">Name</label>
                      <input
                        type="text"
                        placeholder="Treasury Compliance Agent"
                        value={newAgentName}
                        onChange={(e) => setNewAgentName(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="field-label">Topology</label>
                      <select value={newAgentTopology} onChange={(e) => setNewAgentTopology(e.target.value)}>
                        <option value="pregel_supervisor">pregel_supervisor</option>
                        <option value="react_tool_loop">react_tool_loop</option>
                        <option value="plan_execute">plan_execute</option>
                        <option value="verification_gate">verification_gate</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-grid-2" style={{ marginBottom: 10 }}>
                    <div>
                      <label className="field-label">Role</label>
                      <input type="text" value={newAgentRole} onChange={(e) => setNewAgentRole(e.target.value)} />
                    </div>
                    <div>
                      <label className="field-label">Default Provider</label>
                      <select value={newAgentProvider} onChange={(e) => setNewAgentProvider(e.target.value)}>
                        <option value="openai">openai</option>
                        <option value="ollama">ollama</option>
                        <option value="sglang">sglang</option>
                        <option value="vllm">vllm</option>
                      </select>
                    </div>
                  </div>
                  <textarea rows={2} value={newAgentPrompt} onChange={(e) => setNewAgentPrompt(e.target.value)} />
                  <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
                    <button type="button" className="btn" onClick={handleCreateAgent}>
                      Save Agent to SmithDB
                    </button>
                  </div>
                </div>
              </div>

              <div className="split-equal">
                <div>
                  <div className="section-heading">
                    <span className="section-title">SmithDB Waterfall Traces</span>
                  </div>
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Trace</th>
                          <th>Agent</th>
                          <th>Verdict</th>
                          <th>Latency</th>
                          <th>MCSD</th>
                        </tr>
                      </thead>
                      <tbody>
                        {traces.map((t) => (
                          <tr key={t.trace_id}>
                            <td className="mono">{t.trace_id}</td>
                            <td>{t.agent_id}</td>
                            <td>
                              <span className={`pill ${String(t.verdict).includes("ABSTAIN") ? "pill-ochre" : "pill-sage"}`}>
                                {t.verdict}
                              </span>
                            </td>
                            <td className="mono tabular">{t.total_latency_ms} ms</td>
                            <td className="mono tabular">{t.mcsd_speedup_x}x</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="col-divided">
                  <div className="section-heading">
                    <span className="section-title">Pregel Checkpoints &amp; Time-Travel</span>
                  </div>
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Checkpoint</th>
                          <th>Step</th>
                          <th>Node</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {checkpoints.map((c) => (
                          <tr key={c.checkpoint_id}>
                            <td className="mono">{c.checkpoint_id}</td>
                            <td className="mono">S{c.superstep}</td>
                            <td>{c.node_name}</td>
                            <td>
                              <button
                                type="button"
                                className="btn btn-sm"
                                onClick={() => void handleReplayCheckpoint(c.checkpoint_id)}
                              >
                                Replay
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 4: KNOWLEDGE BASES, OCR, DB SYNC, AST & DUCKDB SQL         */}
          {/* ============================================================== */}
          {activeTab === "tab-kb-studio" && (
            <div>
              <div className="subnav-line">
                {(
                  [
                    { id: "documents", label: "KBs & Document OCR Ingest" },
                    { id: "database", label: "Database & Table Sync" },
                    { id: "ast", label: "AST & JEV Explorer" },
                    { id: "sql", label: "DuckDB KAG Workbench" }
                  ] as Array<{ id: KbSubTab; label: string }>
                ).map((sub) => (
                  <button
                    key={sub.id}
                    type="button"
                    className={`subnav-btn ${kbSubTab === sub.id ? "active" : ""}`}
                    onClick={() => {
                      setKbSubTab(sub.id);
                      void refreshKbAndDocs(sub.id);
                    }}
                  >
                    {sub.label}
                  </button>
                ))}
              </div>

              {kbSubTab === "documents" && (
                <div className="split-equal">
                  <div>
                    <div className="section-block">
                      <div className="section-heading">
                        <span className="section-title">Create Knowledge Base</span>
                        <span className="section-note">{kbs.length} active</span>
                      </div>
                      <div className="form-grid-2" style={{ marginBottom: 10 }}>
                        <input
                          type="text"
                          placeholder="Knowledge Base Name"
                          value={kbName}
                          onChange={(e) => setKbName(e.target.value)}
                        />
                        <select value={kbPreset} onChange={(e) => setKbPreset(e.target.value)}>
                          <option value="hrag_jev">hrag_jev (AST + Late Chunking)</option>
                          <option value="table_olap">table_olap (DuckDB Analytical)</option>
                          <option value="paper">paper (Scientific PDF)</option>
                          <option value="laws">laws (Clause Hierarchy)</option>
                          <option value="qa">qa (Q&amp;A Pairs)</option>
                        </select>
                      </div>
                      <div style={{ display: "flex", gap: 10 }}>
                        <input
                          type="text"
                          placeholder="Governance description"
                          value={kbDesc}
                          onChange={(e) => setKbDesc(e.target.value)}
                        />
                        <button type="button" className="btn btn-primary" onClick={handleCreateKb}>
                          Create KB
                        </button>
                      </div>
                    </div>

                    <div className="section-block">
                      <div className="section-heading">
                        <span className="section-title">Multimodal File &amp; OCR Upload</span>
                      </div>
                      <div className="form-grid-2" style={{ marginBottom: 10 }}>
                        <input type="text" value={uploadDocId} onChange={(e) => setUploadDocId(e.target.value)} />
                        <input
                          type="number"
                          min={1}
                          value={uploadVersion}
                          onChange={(e) => setUploadVersion(Number(e.target.value))}
                        />
                      </div>
                      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                        <input type="file" onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
                        <button type="button" className="btn" onClick={handleUploadFile}>
                          Parse &amp; Ingest
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="col-divided">
                    <div className="section-heading">
                      <span className="section-title">Structured Markdown &amp; v2 Merkle Diff</span>
                      <button
                        type="button"
                        className="text-action"
                        onClick={() => {
                          const nextV = ingestVersion + 1;
                          setIngestVersion(nextV);
                          setIngestMarkdown(
                            `${ingestMarkdown}\n\n## Revision Note v${nextV}\nIncremental subtree update at ${new Date().toISOString().slice(11, 19)}.`
                          );
                        }}
                      >
                        Append v+1 Mutation
                      </button>
                    </div>
                    <div className="form-grid-3" style={{ marginBottom: 10 }}>
                      <input type="text" value={ingestDocId} onChange={(e) => setIngestDocId(e.target.value)} />
                      <input type="text" value={ingestUri} onChange={(e) => setIngestUri(e.target.value)} />
                      <input
                        type="number"
                        min={1}
                        value={ingestVersion}
                        onChange={(e) => setIngestVersion(Number(e.target.value))}
                      />
                    </div>
                    <textarea
                      className="code-area"
                      rows={6}
                      value={ingestMarkdown}
                      onChange={(e) => setIngestMarkdown(e.target.value)}
                    />
                    <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className="section-note">
                        {ingestOutput
                          ? `Root #${String(ingestOutput.root_merkle_hash || "").slice(0, 12)} (${ingestOutput.merkle_deltas?.length ?? 0} deltas)`
                          : "Ready for BLAKE3 tree ingest"}
                      </span>
                      <button type="button" className="btn btn-primary" onClick={handleIngestMarkdown}>
                        Ingest Markdown
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {kbSubTab === "database" && (
                <div>
                  <div className="form-grid-3" style={{ marginBottom: 12 }}>
                    <div>
                      <label className="field-label">Target Doc ID</label>
                      <input type="text" value={dbDocId} onChange={(e) => setDbDocId(e.target.value)} />
                    </div>
                    <div>
                      <label className="field-label">DuckDB Table Name</label>
                      <input type="text" value={dbTableName} onChange={(e) => setDbTableName(e.target.value)} />
                    </div>
                    <div>
                      <label className="field-label">Source Mode</label>
                      <select value={dbSourceType} onChange={(e) => setDbSourceType(e.target.value)}>
                        <option value="inline_table">Inline JSON Records</option>
                        <option value="sqlite">Read-Only SQLite Database</option>
                      </select>
                    </div>
                  </div>

                  {dbSourceType === "sqlite" ? (
                    <div className="form-grid-2" style={{ marginBottom: 12 }}>
                      <div>
                        <label className="field-label">SQLite Path</label>
                        <input
                          type="text"
                          className="mono"
                          placeholder="/path/to/database.sqlite3"
                          value={dbSqlitePath}
                          onChange={(e) => setDbSqlitePath(e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="field-label">Read-Only SELECT Query</label>
                        <input
                          type="text"
                          className="mono"
                          value={dbSqliteQuery}
                          onChange={(e) => setDbSqliteQuery(e.target.value)}
                        />
                      </div>
                    </div>
                  ) : (
                    <div style={{ marginBottom: 12 }}>
                      <label className="field-label">Structured JSON Rows</label>
                      <textarea
                        className="code-area"
                        rows={6}
                        value={dbInlineJson}
                        onChange={(e) => setDbInlineJson(e.target.value)}
                      />
                    </div>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className="section-note">{dbSyncStatus || "Tables sync into both DuckDB KAG SQL and H-RAG AST."}</span>
                    <button type="button" className="btn btn-primary" onClick={handleSyncDatabase}>
                      Sync Database Table
                    </button>
                  </div>
                </div>
              )}

              {kbSubTab === "ast" && (
                <div>
                  <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
                    <select
                      style={{ maxWidth: 320 }}
                      value={selectedAstDoc}
                      onChange={(e) => {
                        const docId = e.target.value;
                        setSelectedAstDoc(docId);
                        void vortexApi.getDocumentAst(docId).then(setAstPayload);
                      }}
                    >
                      {documents.map((d) => (
                        <option key={d.doc_id} value={d.doc_id}>
                          {d.doc_id} (v{d.version}, {d.node_count} nodes)
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="split-equal">
                    <div>
                      <div className="section-heading"><span className="section-title">Hierarchical AST Nodes</span></div>
                      {Object.values((astPayload?.ast?.nodes as Record<string, any>) || {}).map((n) => (
                        <div key={n.node_id} className="evidence-entry">
                          <strong>{n.title || n.node_id}</strong>{" "}
                          <span className="mono section-note">{n.node_type} #{String(n.merkle_hash || "").slice(0, 10)}</span>
                          <div style={{ fontSize: 12, color: "var(--ink-secondary)", marginTop: 3 }}>
                            {String(n.content || "").slice(0, 170)}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="col-divided">
                      <div className="section-heading"><span className="section-title">JEV Late-Chunking Spans</span></div>
                      {(astPayload?.jev_chunks || []).map((c: Record<string, any>) => (
                        <div key={c.chunk_id} className="evidence-entry">
                          <span className="mono section-note">
                            {c.node_id} &middot; coherence {Number(c.global_coherence_score ?? 0).toFixed(3)}
                          </span>
                          <div style={{ fontSize: 12, color: "var(--ink-secondary)", marginTop: 3 }}>
                            {String(c.text || "").slice(0, 170)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {kbSubTab === "sql" && (
                <div className="split-equal">
                  <div>
                    <div className="section-heading"><span className="section-title">Registered DuckDB Tables</span></div>
                    {kagTables.map((t) => (
                      <div key={t.table_name} className="evidence-entry">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong className="mono">{t.table_name}</strong>
                          <button
                            type="button"
                            className="btn btn-sm"
                            onClick={() => {
                              const sql = `SELECT * FROM "${t.table_name}" LIMIT 25;`;
                              setKagSql(sql);
                              void vortexApi.runKagSql(sql).then((r) =>
                                setKagSqlOutput({ rows: r.rows, note: `${r.row_count} deterministic rows` })
                              );
                            }}
                          >
                            Query
                          </button>
                        </div>
                        <div className="section-note" style={{ marginTop: 4 }}>
                          {t.row_count} rows &middot; {(t.columns || []).map((c: any) => c.name).join(", ")}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="col-divided">
                    <div className="section-heading">
                      <span className="section-title">Read-Only Analytical SQL</span>
                      <span className="section-note">{kagSqlOutput.note}</span>
                    </div>
                    <textarea className="code-area" rows={4} value={kagSql} onChange={(e) => setKagSql(e.target.value)} />
                    <div style={{ margin: "10px 0 14px", display: "flex", justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() =>
                          void vortexApi
                            .runKagSql(kagSql)
                            .then((r) => setKagSqlOutput({ rows: r.rows, note: `${r.row_count} deterministic rows` }))
                            .catch((err) => setKagSqlOutput({ rows: [], note: String(err) }))
                        }
                      >
                        Run SQL
                      </button>
                    </div>
                    <DataRowsTable rows={kagSqlOutput.rows} emptyMessage="Run a SELECT query above." />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 5: MODELS, OLLAMA & COMPUTE                                */}
          {/* ============================================================== */}
          {activeTab === "tab-runtime" && (
            <div>
              <div className="split-equal section-block">
                <div>
                  <div className="section-heading">
                    <span className="section-title">Model Connector Configuration</span>
                  </div>
                  <div className="form-grid-2" style={{ marginBottom: 10 }}>
                    <div>
                      <label className="field-label">Provider</label>
                      <select value={connProvider} onChange={(e) => setConnProvider(e.target.value)}>
                        <option value="ollama">ollama</option>
                        <option value="openai">openai</option>
                        <option value="vllm">vllm</option>
                        <option value="sglang">sglang</option>
                        <option value="llamacpp">llamacpp</option>
                      </select>
                    </div>
                    <div>
                      <label className="field-label">Display Name</label>
                      <input type="text" value={connName} onChange={(e) => setConnName(e.target.value)} />
                    </div>
                  </div>
                  <div className="form-grid-2" style={{ marginBottom: 12 }}>
                    <div>
                      <label className="field-label">Base URL</label>
                      <input type="text" className="mono" value={connUrl} onChange={(e) => setConnUrl(e.target.value)} />
                    </div>
                    <div>
                      <label className="field-label">Model Identifier</label>
                      <input type="text" className="mono" value={connModel} onChange={(e) => setConnModel(e.target.value)} />
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button type="button" className="btn" onClick={handleDiscoverOllama}>
                      Discover Ollama Models
                    </button>
                    <button type="button" className="btn btn-primary" onClick={handleSaveConnector}>
                      Save Connector
                    </button>
                  </div>

                  {ollamaDiscovery && (
                    <div style={{ marginTop: 14 }}>
                      <div className="section-note" style={{ marginBottom: 6 }}>
                        {ollamaDiscovery.online
                          ? `Ollama online at ${ollamaDiscovery.base_url}: click any model to bind`
                          : `Ollama offline (${ollamaDiscovery.error ?? "unreachable"})`}
                      </div>
                      <div className="text-link-row">
                        {ollamaDiscovery.models.map((m) => (
                          <button
                            key={m.name}
                            type="button"
                            className="text-action mono"
                            onClick={() => {
                              setConnProvider("ollama");
                              setConnModel(m.name);
                            }}
                          >
                            {m.name} ({m.size_gb} GB)
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="col-divided">
                  <div className="section-heading">
                    <span className="section-title">Active Connectors (SmithDB)</span>
                  </div>
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Provider</th>
                          <th>Endpoint</th>
                          <th>Model</th>
                        </tr>
                      </thead>
                      <tbody>
                        {connectors.map((c) => (
                          <tr key={c.connector_id}>
                            <td>{c.name}</td>
                            <td className="mono">{c.provider_type}</td>
                            <td className="mono">{c.base_url}</td>
                            <td className="mono">{c.model_name}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div>
                <div className="section-heading">
                  <span className="section-title">Operator Serving Profiles (Elastic BYO-Accelerator)</span>
                  <span className="section-note">{runtimeCluster?.jax_assessment?.verdict ?? "BYO-Compute"}</span>
                </div>
                <div className="split-equal">
                  {(runtimeCluster?.runtime_profiles || []).map((p: Record<string, any>) => (
                    <div key={p.id} className="evidence-entry">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong>{p.name}</strong>
                        <span className={`pill ${p.status === "online" ? "pill-sage" : "pill-stone"}`}>{p.status}</span>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--ink-secondary)", margin: "4px 0 8px" }}>{p.role}</div>
                      <div className="code-line">{p.command}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* TAB 6: ENTERPRISE SCALE, PROTOCOLS & DEVELOPER FEEDBACK        */}
          {/* ============================================================== */}
          {activeTab === "tab-enterprise" && (
            <div>
              <div className="split-equal section-block">
                <div>
                  <div className="section-heading">
                    <span className="section-title">Developer &amp; Enterprise Feedback</span>
                    <span className="pill pill-sage">
                      Avg {feedbackStats.average_rating} / 5 ({feedbackStats.count})
                    </span>
                  </div>
                  <div className="form-grid-3" style={{ marginBottom: 10 }}>
                    <input type="text" value={fbReviewer} onChange={(e) => setFbReviewer(e.target.value)} />
                    <input type="text" value={fbOrg} onChange={(e) => setFbOrg(e.target.value)} />
                    <select value={fbRating} onChange={(e) => setFbRating(e.target.value)}>
                      <option value="5">5 - Superior</option>
                      <option value="4">4 - Strong</option>
                      <option value="3">3 - Moderate</option>
                      <option value="2">2 - Weak</option>
                      <option value="1">1 - Bug</option>
                    </select>
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Record evaluation findings, SQL accuracy observations, or enterprise deployment needs..."
                    value={fbComment}
                    onChange={(e) => setFbComment(e.target.value)}
                  />
                  <div style={{ margin: "8px 0 14px", display: "flex", justifyContent: "flex-end" }}>
                    <button type="button" className="btn btn-primary btn-sm" onClick={handleSubmitFeedback}>
                      Submit Feedback
                    </button>
                  </div>

                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Reviewer</th>
                          <th>Rating</th>
                          <th>Comment</th>
                        </tr>
                      </thead>
                      <tbody>
                        {feedbackList.map((f) => (
                          <tr key={f.feedback_id}>
                            <td>
                              {f.reviewer}
                              <div className="section-note">{f.organization}</div>
                            </td>
                            <td className="mono">{f.rating}/5</td>
                            <td>{f.comment}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="col-divided">
                  <div className="section-heading">
                    <span className="section-title">Scaling &amp; Protocol Endpoints</span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--ink-secondary)", marginBottom: 10 }}>
                    <strong>Zero-Sprawl Dev Mode:</strong> Single embedded process using SQLite WAL (SmithDB), DuckDB 2.0,
                    and LanceDB.
                  </p>
                  <p style={{ fontSize: 13, color: "var(--ink-secondary)", marginBottom: 12 }}>
                    <strong>Public Multi-Tenant Scale:</strong> Switch SmithDB DSN to PostgreSQL for shared checkpoints,
                    add Redis Streams for background ingestion workers, and connect external vLLM / SGLang / Ollama clusters.
                  </p>
                  <div className="code-line" style={{ marginBottom: 14 }}>
                    curl -s http://127.0.0.1:8420/v1/agents/run -H "Content-Type: application/json" -d
                    '&#123;"query":"Summarize SLAs","agent_id":"vortex-deep-supervisor"&#125;'
                  </div>

                  <div className="section-heading">
                    <span className="section-title">Native A2A &amp; MCP Dispatch</span>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => void vortexApi.callMcp("tools/list", {}).then((r) => setMcpOutput(JSON.stringify(r, null, 2)))}
                    >
                      Inspect MCP Tools
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                    <input type="text" value={a2aInput} onChange={(e) => setA2aInput(e.target.value)} />
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => void vortexApi.callA2A(a2aInput).then((r) => setA2aOutput(JSON.stringify(r, null, 2)))}
                    >
                      Send A2A
                    </button>
                  </div>
                  <div className="code-line" style={{ maxHeight: 190, overflowY: "auto" }}>
                    {mcpOutput || a2aOutput || agentCardText || "Loading A2A agent card..."}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
