# Contributing to Botmartz VORTEX

First off, thank you for considering contributing to **Botmartz VORTEX**! We are building the next generation of zero-sprawl, mathematically deterministic RAG and autonomous agent harnesses, and community feedback, bug reports, and pull requests are warmly welcomed.

---

## 🛠️ Code of Conduct & Core Philosophy

1. **Deterministic Accuracy Over Hallucination**: When dealing with numbers, tables, and analytics, prioritize verifiable execution (DuckDB OLAP SQL, exact citations) over fuzzy LLM approximations.
2. **Zero-Sprawl Footprint**: VORTEX must always run comfortably on a single developer workstation (<500 MB idle memory) without mandating 10+ external Docker containers. Heavy distributed components must remain optional scale-out adapters.
3. **No Breaking Changes to Cryptographic Provenance**: Changes to AST schemas or BLAKE3 Merkle hashing must preserve backward compatibility or provide clear state migration pathways.

---

## 🚀 Setting Up Local Development

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Rust & Cargo (latest stable toolchain)
- Bun 1.1+ (or Node.js 20+)

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/vortex.git
cd vortex
git remote add upstream https://github.com/botmartz/vortex.git
```

### 2. Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Rust Core Crates
Verify that the low-level Rust AST, storage, and Merkle crates compile and pass tests:
```bash
cargo test --workspace
```

### 4. React 19 Studio UI
```bash
cd web
bun install
bun run build # builds static production bundle into python/botmartz_engine/api/static
cd ..
```

### 5. Running the Engine
```bash
uvicorn botmartz_engine.api.server:app --host 127.0.0.1 --port 8420 --reload
```
Navigate to `http://127.0.0.1:8420` to verify the Editorial Light Studio.

---

## 🧪 Running Tests & Quality Gates

Before opening a Pull Request, run the local verification suite:
```bash
# 1. Rust workspace tests
cargo test

# 2. Python engine and API tests
pytest -v python/tests/test_engine.py

# 3. TypeScript typecheck
cd web && bunx tsc --noEmit && cd ..
```

---

## 🗺️ Contribution Roadmap (Where We Need Help!)

- **[ ] Connectors**: Notion, Google Drive, SharePoint, Confluence, and Slack channels into AST trees.
- **[ ] Vector Store Adapters**: Native bindings for Qdrant, Milvus, and pgvector alongside LanceDB.
- **[ ] Multimodal Audio/Video**: WhisperX timestamp alignment mapping into AST node hierarchies.
- **[ ] Interactive Visual DAG Canvas**: A React Flow visual graph editor for human-in-the-loop agent workflows.
- **[ ] Enterprise RBAC**: Row-level and chunk-level security ACL evaluation during retrieval.

---

## 📬 Reporting Issues & Requesting Features

- **Bug Reports**: Open an issue on GitHub with reproduction steps, sample document/query, and system environment.
- **Feature Requests**: Open an RFC issue describing the motivation, technical design, and trade-offs.
- **Enterprise & Community Discord**: Join discussions with our core maintainers and AI architects at [discord.gg/botmartz](https://discord.gg/botmartz) or email `engineering@botmartz.com`.

Thank you for building the frontier of autonomous retrieval systems with us!
