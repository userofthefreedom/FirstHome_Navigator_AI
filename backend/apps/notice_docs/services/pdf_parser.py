from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from django.conf import settings


class PdfParserUnavailable(RuntimeError):
    pass


class RemotePdfFetchError(RuntimeError):
    pass


_PDF_TEXT_CACHE: dict[str, list["PdfPageText"]] = {}


@dataclass(frozen=True)
class PdfPageText:
    page_no: int
    text: str


def parse_pdf_text(
    pdf_path: str | Path,
    *,
    max_pages: int | None = None,
    include_tables: bool = True,
) -> list[PdfPageText]:
    path = Path(pdf_path)
    cache_key = _pdf_text_cache_key(path, max_pages=max_pages, include_tables=include_tables)
    if cache_key:
        cached_pages = _PDF_TEXT_CACHE.get(cache_key)
        if cached_pages is not None:
            return cached_pages

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise PdfParserUnavailable("pypdf is required for PDF parsing. Install backend requirements.") from exc

    reader = PdfReader(str(path))
    table_text_by_page = extract_pdf_table_text(path, max_pages=max_pages) if include_tables else {}
    pages: list[PdfPageText] = []
    for index, page in enumerate(reader.pages):
        if max_pages is not None and index >= max_pages:
            break
        page_no = index + 1
        text_parts = [page.extract_text() or ""]
        table_text = table_text_by_page.get(page_no, "")
        if table_text:
            text_parts.append(table_text)
        pages.append(PdfPageText(page_no=page_no, text="\n".join(part for part in text_parts if part).strip()))
    if cache_key:
        _PDF_TEXT_CACHE[cache_key] = pages
    return pages


def extract_pdf_table_text(pdf_path: str | Path, *, max_pages: int | None = None) -> dict[int, str]:
    try:
        import pdfplumber
    except ModuleNotFoundError:
        return {}

    tables_by_page: dict[int, str] = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for index, page in enumerate(pdf.pages):
                if max_pages is not None and index >= max_pages:
                    break
                rows = _table_rows_from_page(page)
                if rows:
                    tables_by_page[index + 1] = "\n".join(rows)
    except Exception:
        return {}
    return tables_by_page


def _table_rows_from_page(page) -> list[str]:
    rows: list[str] = []
    for table_index, table in enumerate(page.extract_tables() or [], start=1):
        normalized_rows = [_normalize_table_row(row) for row in table or []]
        normalized_rows = [row for row in normalized_rows if row]
        if not normalized_rows:
            continue
        rows.append(f"[table {table_index}]")
        rows.extend(normalized_rows)
    return rows


def _normalize_table_row(row: list[str | None]) -> str:
    cells = [_normalize_table_cell(cell) for cell in row or []]
    return " ".join(cell for cell in cells if cell)


def _normalize_table_cell(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clear_pdf_text_cache() -> None:
    _PDF_TEXT_CACHE.clear()


def _pdf_text_cache_key(pdf_path: Path, *, max_pages: int | None, include_tables: bool) -> str:
    if not getattr(settings, "PDF_TEXT_CACHE_ENABLED", True):
        return ""
    try:
        stat = pdf_path.stat()
    except OSError:
        return ""
    key_payload = "|".join(
        [
            str(pdf_path.resolve()),
            str(stat.st_size),
            str(stat.st_mtime_ns),
            str(max_pages or "all"),
            "tables" if include_tables else "text",
        ]
    )
    return hashlib.sha256(key_payload.encode("utf-8")).hexdigest()


def resolve_local_pdf_path(value: str | None) -> Path | None:
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path))
        return path if path.exists() else None

    if parsed.scheme in {"http", "https"}:
        return None

    path = Path(value)
    if path.exists() and path.suffix.lower() == ".pdf":
        return path
    return None


def download_remote_pdf(
    url: str | None,
    *,
    suggested_name: str = "",
    cache_dir: str | Path | None = None,
    timeout: int = 20,
    max_bytes: int = 30 * 1024 * 1024,
) -> Path | None:
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    target_dir = Path(cache_dir) if cache_dir else settings.BASE_DIR / ".cache" / "official_pdfs"
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    filename = _safe_pdf_filename(suggested_name or Path(parsed.path).name or "official_notice.pdf")
    target_path = target_dir / f"{cache_key}_{filename}"
    if target_path.exists() and target_path.stat().st_size > 0:
        return target_path

    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RemotePdfFetchError(str(exc)) from exc

    content_type = response.headers.get("Content-Type", "").lower()
    bytes_written = 0
    first_chunk = b""
    temp_path = target_path.with_suffix(".tmp")
    try:
        with temp_path.open("wb") as pdf_file:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if not first_chunk:
                    first_chunk = chunk[:8]
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise RemotePdfFetchError("remote PDF exceeded the maximum allowed size")
                pdf_file.write(chunk)

        if bytes_written == 0:
            raise RemotePdfFetchError("remote PDF response was empty")
        if "pdf" not in content_type and not first_chunk.startswith(b"%PDF"):
            raise RemotePdfFetchError("remote document was not a PDF")

        temp_path.replace(target_path)
        return target_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _safe_pdf_filename(value: str) -> str:
    name = Path(unquote(value or "official_notice.pdf")).name
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    name = re.sub(r"[^0-9A-Za-z._-]+", "_", name).strip("._")
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name[:120] or "official_notice.pdf"
