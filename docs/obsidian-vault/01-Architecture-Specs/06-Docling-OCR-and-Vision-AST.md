---
title: 06 — Docling OCR & Vision AST Layout Parser
tags:
  - botmartz
  - spec
  - docling
  - ocr
  - vision
  - pymupdf
  - rapidocr
  - duckdb
  - deepdoc
created: 2026-11-14
owner: botmartz-parser
status: active
---

# 06 — Docling OCR & Vision AST Layout Parser

> [!IMPORTANT]
> **Core Architectural Mission**: Replace brittle regex chunking and multi-gigabyte deep-learning OCR containers with a lightweight, layout-aware document ingestion pipeline. `UniversalDocumentIngestor` parses documents into hierarchical `DocumentAST` trees, tracks bounding boxes, strips repeated headers/footers using DeepDoc heuristics, sorts multi-column text in natural reading order, and automatically extracts structured tables directly into typed [[01-Architecture-Specs/03-CAG-and-KAG-Hybrid-Engine|DuckDB KAG tables]].

---

## 1. High-Level Ingestion Flow

```mermaid
flowchart TD
    RawDoc["Raw Input File (PDF, Image, Markdown, CSV, HTML)"] --> Ingestor["UniversalDocumentIngestor"]
    
    subgraph PDF_Branch ["PDF & Scanned Processing"]
        Ingestor --> PyMu["PyMuPDF (fitz) Engine"]
        PyMu --> RepeatedMargins["DeepDoc Running Header/Footer Filter (>50% freq)"]
        RepeatedMargins --> ColumnSort["Two-Column Spatial Sorter (x_mid midpoint threshold)"]
        ColumnSort --> Dehyphen["Dehyphenation Engine (- \n to continuous token)"]
        PyMu --> NativeTables["PyMuPDF find_tables() Extractor"]
        PyMu -->|Scanned Page (<40 chars)| OCRRouter["OCRProcessor Routing"]
    end

    subgraph OCR_Subsystem ["Hybrid OCR Subsystem"]
        OCRRouter -->|Priority 1: Cloud Vision| OpenAIVision["OpenAI Vision (gpt-4o-mini Precision Markdown)"]
        OCRRouter -->|Priority 2: Sovereign ONNX| Rapid["RapidOCR ONNX (Local CPU/GPU Inference)"]
        OCRRouter -->|Fallback| RawFallback["Text Extraction Stub"]
    end

    subgraph AST_and_KAG ["Hierarchical AST & Deterministic KAG"]
        Dehyphen & NativeTables & OpenAIVision & Rapid --> ASTBuilder["parse_markdown_to_ast()"]
        ASTBuilder --> DocAST["DocumentAST (Hierarchical Sections, Paragraphs, BBoxes)"]
        ASTBuilder --> TableParser["parse_markdown_tables()"]
        TableParser --> TypeInfer["Type Inference Engine (BIGINT, DOUBLE, VARCHAR)"]
        TypeInfer --> DuckDBIngest["DuckDB KAG Schemas & Typed Rows"]
    end

    DocAST --> MerkleTree["Compute BLAKE3 Merkle Hashes"]
    MerkleTree --> JEV["[[01-Architecture-Specs/02-JEV-Late-Chunking|JEV Late-Chunking Embedder]]"]
```

---

## 2. Ingestion Engine Components

### 2.1 `UniversalDocumentIngestor`
Located at `python/botmartz_engine/ingestion/docling_ocr.py`, `UniversalDocumentIngestor` handles multi-modal document parsing into structured AST elements:
- **Markdown & CommonMark**: Parses hierarchical headings (`#` through `######`), code fences (```` ``` ````), tables (`| ... |`), and plain paragraphs, retaining exact character spans (`char_span=(start, end)`).
- **PDF Documents**: Direct vector text extraction, bounding box tracking (`BoundingBox(page, x0, y0, x1, y1)`), running margin detection, and embedded table recognition.
- **Scanned Documents & Images**: Automatic image rasterization at 180 DPI with OCR fallback.
- **Tabular Data (CSV)**: Converts tabular rows into structured markdown representation, feeds into the AST hierarchy, and creates registered typed DuckDB tables.

### 2.2 `OCRProcessor`
The hybrid vision engine encapsulates dual-backend OCR:
1. **OpenAI Vision (`gpt-4o-mini`)**:
   - Encodes image bytes to base64 data URIs.
   - Instructed to transcribe document structure directly into clean GitHub-Flavored Markdown (GFM) preserving table columns and numerical precision.
   - Zero temperature (`temperature=0.0`) ensures deterministic structural transcription.
2. **RapidOCR (`rapidocr_onnxruntime`)**:
   - Embedded ONNX-based local OCR for air-gapped sovereign VPC environments without cloud egress.
   - Extracts bounding boxes and text lines with zero external GPU server requirements.

---

## 3. DeepDoc Lessons & Preprocessing Heuristics

Traditional naive text extractors scramble PDF text, misorder multi-column academic papers, split hyphenated words across chunk boundaries, and pollute vector indices with repeated running headers and footers. Botmartz VORTEX incorporates lessons from Traditional Multi-Container RAG's DeepDoc analysis directly into `ingest_pdf_bytes`:

### 3.1 Running Header & Footer Stripping
```python
# DeepDoc-inspired cross-page running header/footer detection (>50% page frequency)
margin_counts: Dict[str, int] = {}
if len(doc) >= 3:
    for p in doc:
        h = float(p.rect.height)
        seen_on_page: set[str] = set()
        for b in p.get_text("blocks"):
            txt = (b[4] or "").strip()
            # Inspect blocks in top 8% or bottom 8% of the page
            if txt and (b[1] < h * 0.08 or b[3] > h * 0.92):
                seen_on_page.add(txt)
        for txt in seen_on_page:
            margin_counts[txt] = margin_counts.get(txt, 0) + 1

repeated_margins = {t for t, cnt in margin_counts.items() if cnt > len(doc) * 0.5}
```
- **Benefit**: Eliminates boilerplate copyright lines, page numbers, and confidentiality headers from being embedded into chunks, eliminating false positive vector hits.

### 3.2 Two-Column Aware Reading Order
Naive PDF extractors read left-to-right across the entire page width, interweaving column 1 and column 2 into gibberish. VORTEX splits blocks spatially based on the horizontal midpoint:
```python
mid_x = float(page.rect.width) * 0.5
sorted_blocks = sorted(
    blocks,
    key=lambda blk: (0 if blk[2] <= mid_x + 20 else 1, round(blk[1], 1), round(blk[0], 1)),
)
```
- **Ordering**: Column 1 (left) is completely traversed from top to bottom before Column 2 (right) begins, preserving natural semantic flow and paragraph continuity.

### 3.3 Dehyphenation Engine
Line-break hyphens (`inter-\nlocking`) divide single semantic tokens, degrading BM25 keyword matching and dense token embeddings:
```python
dehyphenated = re.sub(r"-\n([a-z])", r"\1", txt)
```
- **Result**: Reconnects hyphenated words across lines while preserving intentional compound words (e.g., `state-of-the-art`).

---

## 4. Automatic DuckDB KAG Table Extraction

> [!TIP]
> **Why Deterministic KAG?** LLMs are notoriously prone to arithmetic calculation errors when reasoning over markdown tables. VORTEX extracts all detected tables, auto-determines column datatypes, and creates structured DuckDB SQL tables.

### 4.1 Table Parsing Pipeline
1. **Header Identification & Deduplication**:
   - Parses Markdown table headers and handles empty or duplicate column names (`_sanitize_identifier`).
   - Ensures column names comply with standard SQL identifier formats (e.g., replacing spaces and special characters with `_`).
2. **Type Inference**:
   - Inspects non-empty column values.
   - Cleans formatting characters (`$`, `,`, `%`).
   - If all values parse as integers $\rightarrow$ typed as `BIGINT`.
   - If values parse as floats $\rightarrow$ typed as `DOUBLE`.
   - Fallback $\rightarrow$ typed as `VARCHAR`.
3. **DuckDB Ingestion**:
   - Generates a typed `DuckDBTableSchema`.
   - Inserts rows into the embedded DuckDB database (`HybridTriadStore.table_mapper`).
   - Makes tables immediately queryable via read-only SQL:
   ```sql
   SELECT "node_id", SUM("vram_gb") AS total_vram 
   FROM "doc_spec_001_table_1" 
   GROUP BY "node_id";
   ```

---

## 5. Architectural Advantages Over Legacy Approaches

| Dimension | Legacy Pipelines (LangChain / LlamaIndex) | Traditional OCR Chunking | Botmartz VORTEX Docling OCR |
| :--- | :--- | :--- | :--- |
| **Document Representation** | Flat string chunks | Visual OCR bounding boxes | **Hierarchical `DocumentAST` with exact BBoxes** |
| **Multi-Column Order** | Scrambled / broken | Heavy ML layout model (YOLOv8) | **Spatial midpoint sorting ($O(N \log N)$)** |
| **Table Handling** | Raw markdown text | HTML table string chunk | **Auto-extracted typed DuckDB KAG tables** |
| **Scanned Page Fallback** | Fails or requires Tesseract | Multi-GB OCR container | **Dual OpenAI Vision + RapidOCR ONNX** |
| **Header/Footer Stripping** | None | Model-based classification | **Frequency-based spatial filtering (>50%)** |
| **RAM Footprint** | Low (text only) | High (4–8 GB ML models) | **<100 MB embedded footprint** |

---

## 6. Linked Specifications
- **[[00-MOC/System-Architecture-MOC|System Architecture MOC]]**
- **[[01-Architecture-Specs/01-H-RAG-and-Merkle-AST|01 — H-RAG Hierarchical AST & BLAKE3 Merkle Versioning]]**
- **[[01-Architecture-Specs/02-JEV-Late-Chunking|02 — JEV Late Chunking Full-Context Embeddings]]**
- **[[01-Architecture-Specs/03-CAG-and-KAG-Hybrid-Engine|03 — CAG Radix KV-Cache & DuckDB KAG Engine]]**
- **[[01-Architecture-Specs/08-Skills-and-Subagents-Catalog|08 — Skills & Subagents Catalog]]**
- **[[02-RFCs/RFC-001-Surpassing-Traditional Multi-Container RAG-Benchmark|RFC-001 — Surpassing Traditional Multi-Container RAG Benchmark]]**
