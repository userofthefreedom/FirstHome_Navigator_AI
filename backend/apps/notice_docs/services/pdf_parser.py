from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


class PdfParserUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PdfPageText:
    page_no: int
    text: str


def parse_pdf_text(pdf_path: str | Path, *, max_pages: int | None = None) -> list[PdfPageText]:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise PdfParserUnavailable("pypdf is required for PDF parsing. Install backend requirements.") from exc

    reader = PdfReader(str(pdf_path))
    pages: list[PdfPageText] = []
    for index, page in enumerate(reader.pages):
        if max_pages is not None and index >= max_pages:
            break
        pages.append(PdfPageText(page_no=index + 1, text=page.extract_text() or ""))
    return pages


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
