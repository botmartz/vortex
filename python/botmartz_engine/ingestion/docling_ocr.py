"""Layout-aware Document & Vision OCR Ingestor (`Docling-style` AST + PyMuPDF + RapidOCR + OpenAI Vision).

Supports Markdown, PDF (text + bounding boxes + tables + scanned page OCR), Images (PNG/JPG/WEBP),
CSV, HTML, and plain text, producing hierarchical `DocumentAST` trees and auto-extracted `DuckDBTableSchema` sets.
"""

from __future__ import annotations

import base64
import csv
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import settings
from ..schemas.core import (
    ASTNode,
    ASTNodeType,
    BoundingBox,
    DocumentAST,
    DuckDBColumnSpec,
    DuckDBTableSchema,
)


def _sanitize_identifier(raw: str, fallback: str = "col") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned[:96]


def _infer_sql_type(values: List[str]) -> str:
    non_empty = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "VARCHAR"
    all_int = True
    all_float = True
    for v in non_empty:
        normalized = v.replace(",", "").replace("$", "").replace("%", "")
        try:
            int(normalized)
        except ValueError:
            all_int = False
        try:
            float(normalized)
        except ValueError:
            all_float = False
    if all_int:
        return "BIGINT"
    if all_float:
        return "DOUBLE"
    return "VARCHAR"


def _coerce_value(val: str, sql_type: str) -> Any:
    s = val.strip()
    if s == "":
        return None
    normalized = s.replace(",", "").replace("$", "").replace("%", "")
    if sql_type == "BIGINT":
        try:
            return int(normalized)
        except ValueError:
            return None
    if sql_type == "DOUBLE":
        try:
            return float(normalized)
        except ValueError:
            return None
    return s


class OCRProcessor:
    """Hybrid Vision & Local OCR engine using RapidOCR and OpenAI Vision (`gpt-4o-mini`)."""

    def __init__(self) -> None:
        self._rapid_ocr: Any = None
        self._rapid_attempted = False

    def _get_rapid_ocr(self) -> Any:
        if not self._rapid_attempted:
            self._rapid_attempted = True
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore

                self._rapid_ocr = RapidOCR()
            except Exception:
                self._rapid_ocr = None
        return self._rapid_ocr

    def extract_text_from_image_bytes(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prefer_vision_llm: bool = True,
    ) -> Tuple[str, str]:
        """Extract markdown/text + tables from an image using OpenAI Vision or RapidOCR.

        Returns `(extracted_markdown, engine_used)`.
        """
        if prefer_vision_llm and settings.openai_api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.openai_api_key)
                b64 = base64.b64encode(image_bytes).decode("ascii")
                resp = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precision Docling OCR parser. Transcribe all headings, paragraphs, "
                                "and tables from the image into clean GitHub-flavored Markdown. Preserve table "
                                "headers and exact numerical values. Output only the extracted Markdown."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all document structure and tables:"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                                },
                            ],
                        },
                    ],
                    max_tokens=1500,
                    temperature=0.0,
                )
                content = (resp.choices[0].message.content or "").strip()
                if content:
                    return content, f"openai-vision:{settings.openai_model}"
            except Exception:
                pass

        rapid = self._get_rapid_ocr()
        if rapid is not None:
            try:
                import numpy as np
                from PIL import Image

                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                result, _ = rapid(np.array(img))
                if result:
                    lines = [item[1] for item in result if len(item) >= 2]
                    return "\n".join(lines), "rapidocr-onnxruntime"
            except Exception:
                pass

        return "[OCR notice: image ingested; no readable text detected or OCR backend unavailable]", "fallback"


class UniversalDocumentIngestor:
    """Layout-aware Document Parser producing H-RAG `DocumentAST` + auto-extracted DuckDB tables."""

    def __init__(self) -> None:
        self.ocr = OCRProcessor()

    def parse_markdown_tables(
        self,
        doc_id: str,
        table_node_id: str,
        table_markdown: str,
        table_index: int,
        section_hint: Optional[str] = None,
    ) -> Optional[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]:
        lines = [ln.strip() for ln in table_markdown.strip().splitlines() if ln.strip()]
        if len(lines) < 3:
            return None

        def _split_row(row_line: str) -> List[str]:
            inner = row_line.strip("|")
            return [cell.strip() for cell in inner.split("|")]

        headers_raw = _split_row(lines[0])
        separator = _split_row(lines[1])
        if not all(re.match(r"^:?-{2,}:?$", c.strip()) for c in separator if c.strip()):
            return None

        col_names = [_sanitize_identifier(h, f"col_{idx+1}") for idx, h in enumerate(headers_raw)]
        # Deduplicate column names
        seen: Dict[str, int] = {}
        unique_cols: List[str] = []
        for c in col_names:
            if c in seen:
                seen[c] += 1
                unique_cols.append(f"{c}_{seen[c]}")
            else:
                seen[c] = 1
                unique_cols.append(c)

        raw_rows: List[List[str]] = []
        for data_line in lines[2:]:
            cells = _split_row(data_line)
            if len(cells) < len(unique_cols):
                cells.extend([""] * (len(unique_cols) - len(cells)))
            raw_rows.append(cells[: len(unique_cols)])

        if not raw_rows:
            return None

        col_specs: List[DuckDBColumnSpec] = []
        for idx, col in enumerate(unique_cols):
            col_vals = [r[idx] for r in raw_rows]
            sql_type = _infer_sql_type(col_vals)
            col_specs.append(DuckDBColumnSpec(name=col, sql_type=sql_type, nullable=True))  # type: ignore[arg-type]

        typed_rows: List[Dict[str, Any]] = []
        for r in raw_rows:
            row_dict = {}
            for idx, spec in enumerate(col_specs):
                row_dict[spec.name] = _coerce_value(r[idx], spec.sql_type)
            typed_rows.append(row_dict)

        base_name = _sanitize_identifier(f"{doc_id}_{section_hint or 'table'}_{table_index}", f"tbl_{table_index}")
        schema = DuckDBTableSchema(
            table_name=base_name,
            doc_id=doc_id,
            source_ast_node_id=table_node_id,
            columns=col_specs,
            row_count=len(typed_rows),
        )
        return schema, typed_rows

    def parse_markdown_to_ast(
        self,
        doc_id: str,
        uri: str,
        markdown_text: str,
        version: int = 1,
        page_bboxes: Optional[Dict[int, BoundingBox]] = None,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]]:
        root_id = f"{doc_id}::root"
        root_node = ASTNode(
            node_id=root_id,
            doc_id=doc_id,
            node_type=ASTNodeType.DOCUMENT,
            title=doc_id,
            content="",
            depth=0,
            structural_path=[doc_id],
            char_span=(0, len(markdown_text)),
        )
        nodes: Dict[str, ASTNode] = {root_id: root_node}
        section_stack: List[ASTNode] = [root_node]
        extracted_tables: List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]] = []

        offset = 0
        lines = markdown_text.splitlines(keepends=True)
        sec_idx = 0
        para_idx = 0
        table_idx = 0
        code_idx = 0

        in_code = False
        code_lines: List[str] = []
        code_start = 0

        in_table = False
        table_lines: List[str] = []
        table_start = 0

        def _attach(parent: ASTNode, node: ASTNode) -> None:
            if parent.children_ids:
                prev_id = parent.children_ids[-1]
                node.prev_sibling_id = prev_id
                nodes[prev_id].next_sibling_id = node.node_id
            parent.children_ids.append(node.node_id)
            nodes[node.node_id] = node

        def _flush_table(end_pos: int) -> None:
            nonlocal in_table, table_lines, table_idx
            if not in_table:
                return
            table_idx += 1
            parent = section_stack[-1]
            node_id = f"{doc_id}::table_{table_idx}"
            tbl_content = "".join(table_lines).strip()
            node = ASTNode(
                node_id=node_id,
                doc_id=doc_id,
                node_type=ASTNodeType.TABLE,
                title=f"Table {table_idx}",
                content=tbl_content,
                depth=parent.depth + 1,
                structural_path=parent.structural_path + [f"Table {table_idx}"],
                parent_id=parent.node_id,
                char_span=(table_start, end_pos),
            )
            _attach(parent, node)
            parsed = self.parse_markdown_tables(
                doc_id=doc_id,
                table_node_id=node_id,
                table_markdown=tbl_content,
                table_index=table_idx,
                section_hint=parent.title,
            )
            if parsed is not None:
                extracted_tables.append(parsed)
            in_table = False
            table_lines = []

        for line_no, line in enumerate(lines, start=1):
            start_char = offset
            end_char = offset + len(line)
            offset = end_char
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_table:
                    _flush_table(start_char)
                if not in_code:
                    in_code = True
                    code_start = start_char
                    code_lines = [line]
                else:
                    code_lines.append(line)
                    code_idx += 1
                    parent = section_stack[-1]
                    node_id = f"{doc_id}::code_{code_idx}"
                    node = ASTNode(
                        node_id=node_id,
                        doc_id=doc_id,
                        node_type=ASTNodeType.CODE_BLOCK,
                        title=f"Code Block {code_idx}",
                        content="".join(code_lines).strip(),
                        depth=parent.depth + 1,
                        structural_path=parent.structural_path,
                        parent_id=parent.node_id,
                        char_span=(code_start, end_char),
                    )
                    _attach(parent, node)
                    in_code = False
                    code_lines = []
                continue

            if in_code:
                code_lines.append(line)
                continue

            if stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    in_table = True
                    table_start = start_char
                    table_lines = []
                table_lines.append(line)
                continue
            elif in_table:
                _flush_table(start_char)

            if not stripped:
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_match:
                sec_idx += 1
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                while len(section_stack) > 1 and section_stack[-1].depth >= level:
                    section_stack.pop()
                parent = section_stack[-1]
                node_id = f"{doc_id}::sec_{sec_idx}"
                node = ASTNode(
                    node_id=node_id,
                    doc_id=doc_id,
                    node_type=ASTNodeType.SECTION if level <= 2 else ASTNodeType.SUBSECTION,
                    title=title,
                    content=stripped,
                    depth=level,
                    structural_path=parent.structural_path + [title],
                    parent_id=parent.node_id,
                    char_span=(start_char, end_char),
                    bbox=page_bboxes.get(line_no) if page_bboxes else None,
                )
                _attach(parent, node)
                section_stack.append(node)
            else:
                para_idx += 1
                parent = section_stack[-1]
                node_id = f"{doc_id}::para_{para_idx}"
                node = ASTNode(
                    node_id=node_id,
                    doc_id=doc_id,
                    node_type=ASTNodeType.PARAGRAPH,
                    title=None,
                    content=stripped,
                    depth=parent.depth + 1,
                    structural_path=parent.structural_path,
                    parent_id=parent.node_id,
                    char_span=(start_char, end_char),
                    bbox=page_bboxes.get(line_no) if page_bboxes else None,
                )
                _attach(parent, node)

        if in_table:
            _flush_table(offset)

        ast = DocumentAST(doc_id=doc_id, uri=uri, version=version, root_id=root_id, nodes=nodes)
        ast.compute_merkle_tree()
        return ast, extracted_tables

    def ingest_pdf_bytes(
        self,
        doc_id: str,
        uri: str,
        pdf_bytes: bytes,
        version: int = 1,
        use_ocr_on_scanned: bool = True,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]], Dict[str, Any]]:
        """Layout-aware PDF parser via PyMuPDF + pymupdf4llm + OCR fallback for scanned pages."""
        import pymupdf as fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        md_sections: List[str] = []
        ocr_pages: List[int] = []
        page_bboxes: Dict[int, BoundingBox] = {}
        line_cursor = 1

        # DeepDoc-inspired cross-page running header/footer detection (>50% page frequency)
        margin_counts: Dict[str, int] = {}
        if len(doc) >= 3:
            for p in doc:
                h = float(p.rect.height)
                seen_on_page: set[str] = set()
                for b in p.get_text("blocks"):
                    txt = (b[4] or "").strip()
                    if txt and (b[1] < h * 0.08 or b[3] > h * 0.92):
                        seen_on_page.add(txt)
                for txt in seen_on_page:
                    margin_counts[txt] = margin_counts.get(txt, 0) + 1
        repeated_margins = {t for t, cnt in margin_counts.items() if cnt > len(doc) * 0.5}

        for page_idx, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks")
            raw_text = (page.get_text("text") or "").strip()

            md_sections.append(f"# Page {page_idx}\n")
            page_bboxes[line_cursor] = BoundingBox(
                page=page_idx, x0=0.0, y0=0.0, x1=float(page.rect.width), y1=float(page.rect.height)
            )
            line_cursor += 1

            if len(raw_text) < 40 and use_ocr_on_scanned:
                pix = page.get_pixmap(dpi=180)
                ocr_text, engine = self.ocr.extract_text_from_image_bytes(
                    pix.tobytes("png"), mime_type="image/png"
                )
                ocr_pages.append(page_idx)
                for ln in ocr_text.splitlines():
                    md_sections.append(ln + "\n")
                    page_bboxes[line_cursor] = BoundingBox(
                        page=page_idx, x0=0.0, y0=0.0, x1=float(page.rect.width), y1=float(page.rect.height)
                    )
                    line_cursor += 1
            else:
                # Two-column aware reading order + dehyphenation + margin stripping
                mid_x = float(page.rect.width) * 0.5
                sorted_blocks = sorted(
                    blocks,
                    key=lambda blk: (0 if blk[2] <= mid_x + 20 else 1, round(blk[1], 1), round(blk[0], 1)),
                )
                for b in sorted_blocks:
                    txt = (b[4] or "").strip()
                    if not txt or txt in repeated_margins:
                        continue
                    dehyphenated = re.sub(r"-\n([a-z])", r"\1", txt)
                    for ln in dehyphenated.splitlines():
                        clean_ln = ln.strip()
                        if clean_ln:
                            md_sections.append(clean_ln + "\n")
                            page_bboxes[line_cursor] = BoundingBox(
                                page=page_idx,
                                x0=float(b[0]),
                                y0=float(b[1]),
                                x1=float(b[2]),
                                y1=float(b[3]),
                            )
                            line_cursor += 1

            # Extract PDF tables natively using PyMuPDF table finder
            try:
                tables = page.find_tables()
                for t in tables.tables:
                    rows_data = t.extract()
                    if rows_data and len(rows_data) >= 2:
                        header = [str(c or "").replace("\n", " ").strip() for c in rows_data[0]]
                        md_sections.append("| " + " | ".join(header) + " |\n")
                        md_sections.append("| " + " | ".join(["---"] * len(header)) + " |\n")
                        line_cursor += 2
                        for row in rows_data[1:]:
                            cells = [str(c or "").replace("\n", " ").strip() for c in row]
                            md_sections.append("| " + " | ".join(cells) + " |\n")
                            line_cursor += 1
                        md_sections.append("\n")
                        line_cursor += 1
            except Exception:
                pass

        full_md = "".join(md_sections)
        ast, extracted_tables = self.parse_markdown_to_ast(
            doc_id=doc_id,
            uri=uri,
            markdown_text=full_md,
            version=version,
            page_bboxes=page_bboxes,
        )
        telemetry = {
            "page_count": len(doc),
            "ocr_pages": ocr_pages,
            "tables_extracted": len(extracted_tables),
        }
        return ast, extracted_tables, telemetry

    def ingest_csv_text(
        self,
        doc_id: str,
        uri: str,
        csv_text: str,
        version: int = 1,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]]]:
        reader = list(csv.reader(io.StringIO(csv_text)))
        if not reader:
            return self.parse_markdown_to_ast(doc_id, uri, "", version=version)
        header = reader[0]
        md_lines = [
            f"# {doc_id} Tabular Dataset\n",
            "| " + " | ".join(header) + " |\n",
            "| " + " | ".join(["---"] * len(header)) + " |\n",
        ]
        for row in reader[1:]:
            md_lines.append("| " + " | ".join(row) + " |\n")
        return self.parse_markdown_to_ast(doc_id, uri, "".join(md_lines), version=version)

    def ingest_file_bytes(
        self,
        doc_id: str,
        filename: str,
        raw_bytes: bytes,
        version: int = 1,
    ) -> Tuple[DocumentAST, List[Tuple[DuckDBTableSchema, List[Dict[str, Any]]]], Dict[str, Any]]:
        ext = Path(filename).suffix.lower()
        uri = f"upload://{filename}"
        if ext == ".pdf":
            return self.ingest_pdf_bytes(doc_id, uri, raw_bytes, version=version)
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            mime = f"image/{'jpeg' if ext in {'.jpg', '.jpeg'} else ext.lstrip('.')}"
            ocr_md, engine = self.ocr.extract_text_from_image_bytes(raw_bytes, mime_type=mime)
            ast, tables = self.parse_markdown_to_ast(doc_id, uri, ocr_md, version=version)
            return ast, tables, {"ocr_engine": engine, "tables_extracted": len(tables)}
        if ext == ".csv":
            ast, tables = self.ingest_csv_text(doc_id, uri, raw_bytes.decode("utf-8", errors="replace"), version=version)
            return ast, tables, {"parser": "csv", "tables_extracted": len(tables)}

        text = raw_bytes.decode("utf-8", errors="replace")
        if ext in {".html", ".htm"}:
            text = re.sub(r"<[^>]+>", " ", text)
        ast, tables = self.parse_markdown_to_ast(doc_id, uri, text, version=version)
        return ast, tables, {"parser": ext or "markdown", "tables_extracted": len(tables)}
