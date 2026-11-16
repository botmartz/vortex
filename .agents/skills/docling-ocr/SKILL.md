---
name: docling-ocr
description: Layout-aware PDF/Document AST parsing, borderless table extraction, bounding-box tracking, and Vision/PyMuPDF OCR ingestion.
---
# Botmartz VORTEX Docling & Vision OCR Skill
- Extract structural headings, paragraphs, code blocks, bounding boxes (`page, x0, y0, x1, y1`), and tables via `pymupdf` (`fitz`) + Vision OCR (`gpt-4o-mini`) fallback for scanned pages/images.
- Automatically register detected Markdown, CSV, and PDF tables into DuckDB KAG schemas.
