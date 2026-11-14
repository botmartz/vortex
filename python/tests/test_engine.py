"""Comprehensive verification suite for Botmartz VORTEX Omni-RAG Engine."""

from __future__ import annotations

import io
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf as fitz
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from botmartz_engine.agents import BotmartzDelegationGraph
from botmartz_engine.api.server import app
from botmartz_engine.schemas import MerkleChangeType


def test_hrag_merkle_jev_kag_cag_and_abstention() -> None:
    with TemporaryDirectory() as tmp:
        graph = BotmartzDelegationGraph(data_dir=Path(tmp), prefer_openai=False)

        doc_v1 = """# 1. Botmartz Thermal & Compute Specification
Our Threadripper cluster utilizes RadixAttention KV caching.
## 1.1 Hardware Inventory
| node_id | vram_gb | kv_hit_rate |
| --- | --- | --- |
| beast-node-01 | 16 | 0.94 |
| beast-node-02 | 24 | 0.97 |

## 1.2 Memory Limits
Each node provides 16 GB dedicated VRAM and 128 GB system RAM.
"""
        ingest_v1 = graph.ingest_markdown(
            doc_id="spec_001",
            uri="file:///docs/spec_001.md",
            markdown_text=doc_v1,
            version=1,
        )
        assert ingest_v1["ast_node_count"] >= 6
        assert ingest_v1["jev_chunk_count"] >= 5
        assert len(ingest_v1["tables_extracted"]) == 1
        assert ingest_v1["merkle_deltas"] == []

        # Mutate only paragraph 2 and verify surgical Merkle diffing
        doc_v2 = doc_v1.replace("16 GB dedicated VRAM", "32 GB dedicated VRAM")
        ingest_v2 = graph.ingest_markdown(
            doc_id="spec_001",
            uri="file:///docs/spec_001.md",
            markdown_text=doc_v2,
            version=2,
        )
        deltas = ingest_v2["merkle_deltas"]
        assert len(deltas) == 1
        assert deltas[0]["change_type"] == MerkleChangeType.MODIFIED.value

        # Hybrid Omni-RAG query + KAG SQL + CAG Radix hit tracking
        tbl_name = ingest_v1["tables_extracted"][0]
        q1 = graph.query(
            query="What is the total VRAM across nodes and RadixAttention policy?",
            sql_override=f'SELECT COUNT(*) AS nodes, SUM("vram_gb") AS total_vram FROM "{tbl_name}"',
            provider="local",
        )
        assert q1["verified"] is True
        assert q1["abstained"] is False
        assert q1["result"]["kag_sql_rows"][0]["total_vram"] == 40
        assert q1["result"]["cag_radix_telemetry"]["radix_cache_hit"] is False

        # Second identical prefix query should register a CAG Radix cache hit
        q2 = graph.query(
            query="How does RadixAttention work in the cluster?",
            provider="local",
            enable_kag_auto_sql=False,
        )
        assert q2["verified"] is True
        assert q2["result"]["cag_radix_telemetry"]["radix_cache_hit"] is True

        # Out-of-scope query must trigger Evidence-Grounded Abstention Sentinel
        q_abs = graph.query(
            query="zzzzxq nonexistent mars colony wheat harvest 2099",
            provider="local",
            enable_kag_auto_sql=False,
        )
        assert q_abs["abstained"] is True
        assert q_abs["verified"] is False
        assert q_abs["verdict"] == "ABSTAINED_INSUFFICIENT_EVIDENCE"


def test_pdf_and_image_ocr_ingestion() -> None:
    with TemporaryDirectory() as tmp:
        graph = BotmartzDelegationGraph(data_dir=Path(tmp), prefer_openai=False)

        # Generate a real synthetic PDF with PyMuPDF
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        page.insert_text((72, 72), "Botmartz Sovereign Compliance Report\n\nAll nodes pass ISO 27001 audit.")
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        pdf_res = graph.ingest_file(doc_id="iso_pdf", filename="compliance.pdf", raw_bytes=pdf_bytes)
        assert pdf_res["ast_node_count"] >= 3
        assert pdf_res["parser_telemetry"]["page_count"] == 1

        # Generate a synthetic PNG image with clear text for RapidOCR / OCR pipeline
        img = Image.new("RGB", (600, 140), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 45), "BOTMARTZ VORTEX OCR VERIFIED", fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_res = graph.ingest_file(doc_id="ocr_img", filename="scan.png", raw_bytes=buf.getvalue())
        assert img_res["ast_node_count"] >= 1


def test_fastapi_a2a_mcp_and_live_endpoints() -> None:
    client = TestClient(app)

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["engine"] == "botmartz-vortex"
    assert h.json()["duckdb_tables"] >= 2

    # Test UI HTML served at /
    ui = client.get("/")
    assert ui.status_code == 200
    assert "Botmartz VORTEX Studio" in ui.text

    # Test A2A Agent Card
    card = client.get("/.well-known/agent.json")
    assert card.status_code == 200
    assert card.json()["name"] == "Botmartz VORTEX Omni-RAG Engine"

    # Test A2A JSON-RPC tasks/send (architect & parser)
    a2a_arch = client.post(
        "/a2a",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "agentId": "botmartz-architect",
                "message": {"role": "user", "parts": [{"type": "text", "text": "Inspect system"}]},
            },
        },
    )
    assert a2a_arch.status_code == 200
    assert a2a_arch.json()["result"]["status"]["state"] == "completed"

    # Test MCP JSON-RPC initialize & tools/list & tools/call
    mcp_init = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert mcp_init.status_code == 200
    assert mcp_init.json()["result"]["serverInfo"]["name"] == "botmartz-vortex-mcp"

    mcp_tools = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert len(mcp_tools.json()["result"]["tools"]) == 6

    tables_res = client.get("/v1/kag/tables")
    assert tables_res.status_code == 200
    workstation_tbl = next(t["table_name"] for t in tables_res.json()["tables"] if "sovereign_workstation" in t["table_name"])

    mcp_call = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "vortex_kag_sql_query",
                "arguments": {
                    "sql": f'SELECT COUNT(*) AS cnt, SUM("gpu_vram_gb") AS sum_vram FROM "{workstation_tbl}"'
                },
            },
        },
    )
    assert mcp_call.status_code == 200
    assert '"sum_vram": 120' in mcp_call.json()["result"]["content"][0]["text"]


def test_runtime_cluster_and_live_benchmark() -> None:
    client = TestClient(app)

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["version"] == "0.3.0"

    # Verify v0.3 UI tabs & multi-theme tokens are served without hardcoded GPU marketing disclosures
    ui = client.get("/")
    assert ui.status_code == 200
    assert "Botmartz VORTEX Studio" in ui.text
    assert "tab-superiority" in ui.text
    assert "tab-runtime" in ui.text
    assert "tab-agents" in ui.text
    assert "#D4A373" in ui.text
    assert "2x RTX 5080" not in ui.text

    # Verify elastic runtime profiles & JAX advisory
    rt = client.get("/v1/runtime/cluster")
    assert rt.status_code == 200
    rt_data = rt.json()
    assert "hardware" in rt_data
    assert "runtime_profiles" in rt_data
    profile_ids = {p["id"] for p in rt_data["runtime_profiles"]}
    assert {"sglang_radix", "vllm_apc", "llamacpp_cuda", "ollama_local", "openai_support"}.issubset(
        profile_ids
    )
    assert rt_data["jax_assessment"]["jax_required"] is False

    # Verify Live 4-stage Benchmark
    bench = client.post("/v1/benchmark/run")
    assert bench.status_code == 200
    b_data = bench.json()
    assert b_data["status"] == "passed"
    metrics = b_data["measured_metrics"]
    assert metrics["total_ast_nodes"] >= 15
    assert metrics["nodes_skipped_pct"] >= 70.0
    assert len(b_data["competitor_baselines"]) >= 3


def test_v03_smithdb_deep_agents_duel_db_ingest_and_feedback() -> None:
    client = TestClient(app)

    # 1. Managed Agents list & custom registration in SmithDB
    ag_list = client.get("/v1/agents")
    assert ag_list.status_code == 200
    assert len(ag_list.json()["agents"]) >= 4

    created_ag = client.post(
        "/v1/agents",
        json={
            "agent_id": "test-treasury-agent",
            "name": "Treasury SQL Agent",
            "role": "Deterministic Treasury Auditor",
            "topology": "pregel_supervisor",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )
    assert created_ag.status_code == 200
    assert created_ag.json()["agent"]["agent_id"] == "test-treasury-agent"

    # 2. Run 4-Superstep Pregel Deep Agent Harness & verify SmithDB traces/checkpoints + Replay
    run_res = client.post(
        "/v1/agents/run",
        json={
            "query": "What is the total system_ram_gb across the cluster nodes?",
            "agent_id": "test-treasury-agent",
            "provider": "openai",
            "enable_speculative": True,
        },
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["verdict"] == "VERIFIED_GROUNDED"
    assert len(run_data["checkpoints"]) == 4
    assert run_data["ear_routing"]["shannon_entropy"] > 0.0
    assert "estimated_speedup_x" in run_data["mcsd_speculative"]
    assert run_data["scg_claims"]["claim_count"] >= 1

    traces_res = client.get("/v1/smithdb/traces")
    assert traces_res.status_code == 200
    assert any(t["trace_id"] == run_data["trace_id"] for t in traces_res.json()["traces"])

    cp_id = run_data["checkpoints"][0]["checkpoint_id"]
    cps_res = client.get(f"/v1/smithdb/checkpoints?thread_id={run_data['thread_id']}")
    assert cps_res.status_code == 200
    assert len(cps_res.json()["checkpoints"]) >= 4

    replay_res = client.post("/v1/smithdb/replay", json={"checkpoint_id": cp_id})
    assert replay_res.status_code == 200
    assert replay_res.json()["replayed_from_checkpoint"] == cp_id

    # 3. Side-by-Side RAGFlow vs VORTEX Live Duel
    duel_res = client.post(
        "/v1/duel/ragflow",
        json={
            "query": "Calculate total gpu_vram_gb and compare container count vs RAGFlow",
            "provider": "openai",
        },
    )
    assert duel_res.status_code == 200
    duel_data = duel_res.json()
    assert duel_data["ragflow"]["total_flat_chunks"] >= 1
    assert duel_data["vortex"]["verdict"] == "VERIFIED_GROUNDED"
    assert len(duel_data["architecture_comparison"]) >= 8

    # 4. Knowledge Bases & Database Table Ingestion
    kb_res = client.post(
        "/v1/kb",
        json={"kb_id": "kb-qa-test", "name": "QA Test KB", "chunk_preset": "table_olap"},
    )
    assert kb_res.status_code == 200

    db_ing = client.post(
        "/v1/ingest/db",
        json={
            "doc_id": "test_rev_db",
            "kb_id": "kb-qa-test",
            "source_type": "inline_table",
            "table_name": "regional_arr",
            "rows": [
                {"region": "NA", "arr": 500},
                {"region": "EU", "arr": 300},
            ],
        },
    )
    assert db_ing.status_code == 200
    assert db_ing.json()["imported_rows"] == 2
    assert len(db_ing.json()["tables_extracted"]) >= 1

    # 5. Connectors & Developer Feedback
    conns = client.get("/v1/connectors")
    assert conns.status_code == 200
    assert len(conns.json()["connectors"]) >= 5

    fb_post = client.post(
        "/v1/feedback",
        json={
            "trace_id": run_data["trace_id"],
            "reviewer": "Pytest Suite",
            "rating": 5,
            "category": "v0.3_verification",
            "comment": "Pregel harness, SmithDB replay, and RAGFlow duel verified.",
        },
    )
    assert fb_post.status_code == 200
    fb_list = client.get("/v1/feedback")
    assert fb_list.status_code == 200
    assert fb_list.json()["count"] >= 1


