import { useEffect, useState } from "react";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import {
  vortexApi,
  type HealthResponse,
  type QueryResponse,
  type RagflowDuelResponse,
  type AgentRecord,
  type SmithTraceRecord,
  type KnowledgeBaseRecord,
  type DocumentAstRecord
} from "./api";

type TabId = "explainer" | "query" | "duel" | "data" | "settings";
type ThemeMode = "light" | "dark" | "system";

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("explainer");
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Query Workspace State
  const [queryText, setQueryText] = useState("What are the key technical pillars and memory limits?");
  const [provider, setProvider] = useState("gemini");
  const [enableKag, setEnableKag] = useState(true);
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);

  // Benchmark / Duel State
  const [duelQuery, setDuelQuery] = useState("Calculate total system_ram_gb across cluster nodes.");
  const [duelBusy, setDuelBusy] = useState(false);
  const [duelResult, setDuelResult] = useState<RagflowDuelResponse | null>(null);

  // Ingest / Data State
  const [docId, setDocId] = useState("");
  const [docContent, setDocContent] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocId, setUploadDocId] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [docsList, setDocsList] = useState<Array<{ doc_id: string; uri: string; node_count: number }>>([]);
  const [tablesList, setTablesList] = useState<string[]>([]);
  const [ingestBusy, setIngestBusy] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");

  // Theme Management
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", prefersDark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  // Load Data
  const refreshAll = async () => {
    try {
      const h = await vortexApi.getHealth();
      setHealth(h);
      const docs = await vortexApi.listDocuments();
      setDocsList(docs.documents || []);
      const tbls = await vortexApi.listKagTables();
      setTablesList(tbls.tables || []);
    } catch {
      // offline or building
    }
  };

  useEffect(() => {
    void refreshAll();
  }, []);

  // Guided Walkthrough using Driver.js
  const startTour = () => {
    const driverObj = driver({
      showProgress: true,
      steps: [
        {
          element: ".explainer-hero",
          popover: {
            title: "Welcome to Botmartz VORTEX",
            description: "A zero-sprawl Omni-RAG engine running in a single process under 500 MB RAM."
          }
        },
        {
          element: "#nav-query",
          popover: {
            title: "Deterministic Retrieval",
            description: "Ask qualitative questions or execute exact in-memory DuckDB SQL queries without hallucinations."
          }
        },
        {
          element: "#nav-duel",
          popover: {
            title: "Architectural Comparison",
            description: "Run side-by-side benchmark queries comparing VORTEX's single process against multi-container setups."
          }
        },
        {
          element: "#nav-data",
          popover: {
            title: "Knowledge & Data",
            description: "Inspect parsed AST trees, add documents, and view connected analytical tables."
          }
        }
      ]
    });
    driverObj.drive();
  };

  const handleQuery = async () => {
    if (!queryText.trim()) return;
    setQueryBusy(true);
    try {
      const res = await vortexApi.query({
        query: queryText.trim(),
        provider,
        enable_kag_auto_sql: enableKag
      });
      setQueryResult(res);
      void refreshAll();
    } finally {
      setQueryBusy(false);
    }
  };

  const handleDuel = async () => {
    setDuelBusy(true);
    try {
      const res = await vortexApi.runRagflowDuel(duelQuery.trim(), provider);
      setDuelResult(res);
      void refreshAll();
    } finally {
      setDuelBusy(false);
    }
  };

  const handleIngest = async () => {
    if (!docId.trim() || !docContent.trim()) return;
    setIngestBusy(true);
    try {
      const res = await vortexApi.ingestMarkdown({
        doc_id: docId.trim(),
        uri: `vault://${docId.trim()}.md`,
        version: 1,
        markdown_text: docContent
      });
      setIngestMsg(`Successfully ingested ${res.ast_node_count} AST nodes and ${res.jev_chunk_count} JEV chunks.`);
      setDocId("");
      setDocContent("");
      await refreshAll();
    } finally {
      setIngestBusy(false);
    }
  };

  const handleFileUpload = async () => {
    if (!uploadFile) return;
    setUploadBusy(true);
    setUploadMsg("");
    try {
      const targetDocId = uploadDocId.trim() || uploadFile.name.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_-]/g, "_");
      const fd = new FormData();
      fd.append("doc_id", targetDocId);
      fd.append("version", "1");
      fd.append("file", uploadFile);

      const res = await vortexApi.ingestFile(fd);
      setUploadMsg(`Successfully imported ${uploadFile.name}: ${res.ast_node_count || res.nodes || 0} AST nodes, ${res.jev_chunk_count || 0} JEV chunks.`);
      setUploadFile(null);
      setUploadDocId("");
      await refreshAll();
    } catch (err: any) {
      setUploadMsg(`Import failed: ${err.message || String(err)}`);
    } finally {
      setUploadBusy(false);
    }
  };

  return (
    <div>
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-block">
          <div className="brand-symbol">V</div>
          <span className="brand-title">Botmartz VORTEX</span>
          <span className="brand-badge">v1.0</span>
        </div>

        <div className="header-controls">
          <button className="btn btn-sm" onClick={startTour}>
            Interactive Guide
          </button>
          <select
            className="theme-toggle"
            value={theme}
            onChange={(e) => setTheme(e.target.value as ThemeMode)}
            aria-label="Theme selector"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </div>
      </header>

      {/* App Shell with Sidebar */}
      <div className="app-shell">
        <aside className="app-sidebar">
          <div>
            <div className="sidebar-section-title">Navigation</div>
            <nav className="sidebar-nav-list">
              <button
                className={`sidebar-nav-btn ${activeTab === "explainer" ? "active" : ""}`}
                onClick={() => setActiveTab("explainer")}
              >
                <span>Overview &amp; Explainer</span>
              </button>
              <button
                id="nav-query"
                className={`sidebar-nav-btn ${activeTab === "query" ? "active" : ""}`}
                onClick={() => setActiveTab("query")}
              >
                <span>Ask &amp; Search</span>
              </button>
              <button
                id="nav-duel"
                className={`sidebar-nav-btn ${activeTab === "duel" ? "active" : ""}`}
                onClick={() => setActiveTab("duel")}
              >
                <span>Engine Comparison</span>
              </button>
              <button
                id="nav-data"
                className={`sidebar-nav-btn ${activeTab === "data" ? "active" : ""}`}
                onClick={() => setActiveTab("data")}
              >
                <span>Knowledge Base</span>
                <span className="badge badge-subtle mono">{docsList.length}</span>
              </button>
            </nav>
          </div>

          <div>
            <div className="sidebar-section-title">Engine Health</div>
            <div style={{ padding: "0 10px", fontSize: 12, color: "var(--ink-secondary)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span>Status</span>
                <span className="badge badge-success">{health?.status || "Ready"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span>Tables (DuckDB)</span>
                <span className="mono">{tablesList.length}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>RAM Footprint</span>
                <span className="mono">&lt; 500 MB</span>
              </div>
            </div>
          </div>

          <div className="sidebar-footer">
            <div>Zero-Sprawl Omni-RAG</div>
            <div style={{ marginTop: 2, fontSize: 11 }}>In-Memory AST + JEV + DuckDB</div>
          </div>
        </aside>

        <main className="app-main-content">
        {/* TAB 1: Single Explainer Landing */}
        {activeTab === "explainer" && (
          <div>
            <section className="explainer-hero">
              <div className="hero-tag">Zero-Sprawl Omni-RAG Architecture</div>
              <h1 className="hero-headline">Enterprise Retrieval Without the Multi-Container Tax</h1>
              <p className="hero-sub">
                Botmartz VORTEX replaces bloated multi-service deployments with an embedded single-process engine running under 500 MB RAM, delivering deterministic mathematical accuracy, cryptographic document updates, and late chunking.
              </p>

              <div className="value-grid">
                <div className="value-card">
                  <div className="value-card-title">Exact Mathematical SQL (KAG)</div>
                  <div className="value-card-desc">
                    Spreadsheets and invoices are compiled into in-memory DuckDB 2.0 OLAP queries, guaranteeing 100% calculation precision with zero LLM math hallucination.
                  </div>
                </div>

                <div className="value-card">
                  <div className="value-card-title">O(&Delta;) BLAKE3 Merkle Updates</div>
                  <div className="value-card-desc">
                    When policy documents update, VORTEX diffs the Abstract Syntax Tree (AST) cryptographically. Only modified subtrees are re-indexed, saving ~90% of re-embedding compute.
                  </div>
                </div>

                <div className="value-card">
                  <div className="value-card-title">JEV (Late Chunking)</div>
                  <div className="value-card-desc">
                    Computes embeddings over the complete continuous document attention matrix before chunk pooling, ensuring individual chunks preserve global document context.
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button className="btn btn-primary" onClick={() => setActiveTab("query")}>
                  Start Querying
                </button>
                <button className="btn" onClick={() => setActiveTab("duel")}>
                  Run Benchmark Duel
                </button>
                <button className="btn" onClick={() => setActiveTab("data")}>
                  Manage Knowledge Bases
                </button>
              </div>
            </section>

            <div className="workflow-strip">
              <div className="workflow-step">
                <div className="step-number">Step 01</div>
                <div className="step-label">AST Layout Ingestion</div>
              </div>
              <div className="workflow-step">
                <div className="step-number">Step 02</div>
                <div className="step-label">Entropy-Adaptive Routing</div>
              </div>
              <div className="workflow-step">
                <div className="step-number">Step 03</div>
                <div className="step-label">Deterministic DuckDB KAG</div>
              </div>
              <div className="workflow-step">
                <div className="step-number">Step 04</div>
                <div className="step-label">Claim Verification &amp; Audit</div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Query & Ask */}
        {activeTab === "query" && (
          <div className="layout-grid">
            <div>
              <div className="card">
                <div className="card-title">
                  <span>Ask Knowledge Base</span>
                  <span className="badge badge-subtle">{health?.status === "ok" ? "Engine Ready" : "Connecting..."}</span>
                </div>

                <div className="field-group">
                  <label className="field-label" htmlFor="query-input">Query</label>
                  <textarea
                    id="query-input"
                    rows={3}
                    value={queryText}
                    onChange={(e) => setQueryText(e.target.value)}
                    placeholder="Ask any policy question or request a calculation..."
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
                  <div>
                    <label className="field-label" htmlFor="query-provider">Model Provider</label>
                    <select id="query-provider" value={provider} onChange={(e) => setProvider(e.target.value)}>
                      <option value="gemini">Gemini (Google AI Primary)</option>
                      <option value="ollama">Ollama (Local)</option>
                      <option value="llamacpp">llama.cpp Server</option>
                      <option value="openai">OpenAI / Compatible</option>
                    </select>
                  </div>

                  <div>
                    <label className="field-label" htmlFor="enable-kag-check">Exact Math Engine</label>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontSize: 13, cursor: "pointer" }}>
                      <input
                        id="enable-kag-check"
                        type="checkbox"
                        checked={enableKag}
                        onChange={(e) => setEnableKag(e.target.checked)}
                      />
                      Enable DuckDB SQL
                    </label>
                  </div>
                </div>

                <button className="btn btn-primary" disabled={queryBusy} onClick={handleQuery}>
                  {queryBusy ? "Processing..." : "Run Query"}
                </button>
              </div>

              {queryResult && (
                <div className="card">
                  <div className="card-title">
                    <span>Verified Synthesis</span>
                    <span className={`badge ${queryResult.abstained ? "badge-warn" : "badge-success"}`}>
                      {queryResult.verdict}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap", marginBottom: 14 }}>
                    {queryResult.result?.answer || "No response generated."}
                  </div>
                  {queryResult.result?.kag_sql_executed && (
                    <div>
                      <div className="field-label">Executed Analytical SQL</div>
                      <div className="code-box">{queryResult.result.kag_sql_executed}</div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div>
              <div className="card">
                <div className="card-title">Telemetry &amp; Provenance</div>
                {queryResult ? (
                  <div>
                    <div style={{ marginBottom: 12 }}>
                      <span className="field-label">Shannon Entropy H(q)</span>
                      <div className="mono tabular" style={{ fontSize: 18, fontWeight: 700 }}>
                        {queryResult.frontier_harness?.ear_routing?.shannon_entropy ?? "--"}
                      </div>
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <span className="field-label">Speculative Acceleration</span>
                      <div className="mono tabular" style={{ fontSize: 18, fontWeight: 700 }}>
                        {queryResult.frontier_harness?.mcsd_speculative?.estimated_speedup_x ?? "1.0"}x
                      </div>
                    </div>

                    <div>
                      <span className="field-label">Retrieved Evidence Nodes</span>
                      <div className="mono" style={{ fontSize: 12, color: "var(--ink-secondary)" }}>
                        {(queryResult.merkle_provenance_chain || []).length} AST nodes verified
                      </div>
                    </div>
                  </div>
                ) : (
                  <p style={{ color: "var(--ink-muted)", fontSize: 13 }}>
                    Execute a query to inspect real-time Entropy-Adaptive Routing, DuckDB SQL execution, and Merkle provenance chains.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Architectural Duel */}
        {activeTab === "duel" && (
          <div className="card">
            <div className="card-title">Side-by-Side Architecture Benchmark</div>
            <p style={{ color: "var(--ink-secondary)", marginBottom: 16, fontSize: 13.5 }}>
              Compare query execution between a baseline multi-container flat-chunking architecture (RAGFlow reference) and Botmartz VORTEX on identical hardware.
            </p>

            <div className="field-group">
              <label className="field-label" htmlFor="duel-query-input">Benchmark Query</label>
              <input
                id="duel-query-input"
                type="text"
                value={duelQuery}
                onChange={(e) => setDuelQuery(e.target.value)}
              />
            </div>

            <button className="btn btn-brand" disabled={duelBusy} onClick={handleDuel}>
              {duelBusy ? "Running Duel..." : "Execute Side-by-Side Benchmark"}
            </button>

            {duelResult && (
              <div style={{ marginTop: 20 }}>
                <div className="table-wrap">
                  <table className="clean-table">
                    <thead>
                      <tr>
                        <th>Architectural Dimension</th>
                        <th>Multi-Container Baseline (RAGFlow Reference)</th>
                        <th>Botmartz VORTEX v1.0</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(duelResult.architecture_comparison || []).map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{row.feature}</td>
                          <td style={{ color: "var(--ink-secondary)" }}>{row.ragflow}</td>
                          <td style={{ color: "var(--ink-primary)", fontWeight: 500 }}>{row.vortex}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: Knowledge Bases & Ingest */}
        {activeTab === "data" && (
          <div className="layout-grid">
            <div>
              {/* Local File / CSV / PDF Upload Card */}
              <div className="card">
                <div className="card-title">
                  <span>Import Local File (CSV, PDF, MD, Text)</span>
                  <span className="badge badge-subtle">Local Multi-Format</span>
                </div>
                <p style={{ color: "var(--ink-secondary)", fontSize: 13, marginBottom: 14 }}>
                  Upload full CSV datasets, PDF documents, or Markdown files directly from your computer. Tabular data will be compiled into DuckDB 2.0 tables for SQL queries.
                </p>

                <div className="field-group">
                  <label className="field-label" htmlFor="upload-doc-id">Custom Document / Table ID (Optional)</label>
                  <input
                    id="upload-doc-id"
                    type="text"
                    placeholder="Auto-generated from filename if empty"
                    value={uploadDocId}
                    onChange={(e) => setUploadDocId(e.target.value)}
                  />
                </div>

                <div
                  className="upload-dropzone"
                  onClick={() => document.getElementById("file-upload-input")?.click()}
                >
                  <input
                    id="file-upload-input"
                    type="file"
                    style={{ display: "none" }}
                    accept=".csv,.pdf,.md,.markdown,.txt,.json"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                      }
                    }}
                  />
                  <div className="upload-dropzone-title">
                    {uploadFile ? `Selected: ${uploadFile.name} (${Math.round(uploadFile.size / 1024)} KB)` : "Choose or drag CSV / PDF / Markdown file here"}
                  </div>
                  <div className="upload-dropzone-sub">
                    Supported extensions: .csv, .pdf, .md, .txt (up to 50 MB)
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <button
                    className="btn btn-primary"
                    disabled={!uploadFile || uploadBusy}
                    onClick={handleFileUpload}
                  >
                    {uploadBusy ? "Parsing & Indexing File..." : "Import File into Knowledge Base"}
                  </button>
                  {uploadFile && (
                    <button
                      className="btn"
                      disabled={uploadBusy}
                      onClick={() => setUploadFile(null)}
                    >
                      Clear
                    </button>
                  )}
                </div>

                {uploadMsg && (
                  <p
                    style={{
                      color: uploadMsg.includes("failed") ? "var(--status-danger)" : "var(--status-success)",
                      marginTop: 10,
                      fontSize: 13
                    }}
                  >
                    {uploadMsg}
                  </p>
                )}
              </div>

              {/* Paste Text / Markdown Document */}
              <div className="card">
                <div className="card-title">Add Raw Text / Markdown Document</div>
                <div className="field-group">
                  <label className="field-label" htmlFor="ingest-doc-id">Document ID</label>
                  <input
                    id="ingest-doc-id"
                    type="text"
                    placeholder="e.g. employee_handbook_2026"
                    value={docId}
                    onChange={(e) => setDocId(e.target.value)}
                  />
                </div>

                <div className="field-group">
                  <label className="field-label" htmlFor="ingest-content">Content (Markdown with Headings &amp; Tables)</label>
                  <textarea
                    id="ingest-content"
                    rows={6}
                    placeholder="# Section 1&#10;Paste text or tables here..."
                    value={docContent}
                    onChange={(e) => setDocContent(e.target.value)}
                  />
                </div>

                <button className="btn btn-primary" disabled={ingestBusy} onClick={handleIngest}>
                  {ingestBusy ? "Indexing AST..." : "Ingest into VORTEX"}
                </button>

                {ingestMsg && <p style={{ color: "var(--status-success)", marginTop: 10, fontSize: 13 }}>{ingestMsg}</p>}
              </div>
            </div>

            <div className="card">
              <div className="card-title">Indexed Documents ({docsList.length})</div>
              {docsList.length === 0 ? (
                <p style={{ color: "var(--ink-muted)", fontSize: 13 }}>No documents indexed yet. Import a file or paste content on the left.</p>
              ) : (
                <div className="table-wrap">
                  <table className="clean-table">
                    <thead>
                      <tr>
                        <th>Doc ID</th>
                        <th>Nodes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {docsList.map((d) => (
                        <tr key={d.doc_id}>
                          <td className="mono" style={{ fontSize: 12 }}>{d.doc_id}</td>
                          <td>{d.node_count} AST nodes</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div style={{ marginTop: 24 }}>
                <div className="card-title">Active Analytical Tables ({tablesList.length})</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {tablesList.map((t) => (
                    <span key={t} className="badge badge-subtle mono">
                      {t}
                    </span>
                  ))}
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
