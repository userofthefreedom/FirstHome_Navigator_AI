from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from apps.notice_docs.services.pdf_parser import PdfPageText


MONEY_TERMS = ("주택가격", "공급금액", "분양가격", "계약금", "중도금", "잔금", "융자금", "납부")
ELIGIBILITY_TERMS = ("무주택", "소득", "자산", "청약통장", "거주", "우선공급", "특별공급", "제출서류")
PURPOSE_QUERIES = {
    "unit_options": ("주택형 전용면적 주택가격 공급금액 계약금 중도금 잔금 융자금", MONEY_TERMS),
    "payment_schedule": ("계약금 중도금 잔금 납부일 납부일정 회차", MONEY_TERMS),
    "eligibility": ("무주택 소득 자산 청약통장 거주 우선공급 특별공급 제출서류", ELIGIBILITY_TERMS),
}


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    page_no: int
    block_type: str
    text: str


@dataclass(frozen=True)
class RankedChunk:
    chunk: DocumentChunk
    score: float
    matched_terms: tuple[str, ...]


def build_document_chunks(
    pages: list[PdfPageText],
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for page in pages:
        table_blocks, remaining_text = _extract_table_blocks(page.text)
        for table_index, table_text in enumerate(table_blocks, start=1):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"p{page.page_no}-table-{table_index}",
                    page_no=page.page_no,
                    block_type="table",
                    text=table_text,
                )
            )

        for paragraph_index, paragraph in enumerate(_split_paragraphs(remaining_text), start=1):
            for segment_index, segment in enumerate(_window_text(paragraph, max_chars=max_chars, overlap_chars=overlap_chars), start=1):
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"p{page.page_no}-paragraph-{paragraph_index}-{segment_index}",
                        page_no=page.page_no,
                        block_type="paragraph",
                        text=segment,
                    )
                )
    return chunks


def search_document_chunks(
    pages: list[PdfPageText],
    query: str,
    *,
    keywords: Iterable[str] = (),
    limit: int = 8,
) -> list[RankedChunk]:
    chunks = build_document_chunks(pages)
    query_terms = tuple(dict.fromkeys([*_terms(query), *[term for term in keywords if term]]))
    ranked = [_rank_chunk(chunk, query_terms) for chunk in chunks]
    ranked = [item for item in ranked if item.score > 0]
    ranked.sort(key=lambda item: (item.score, item.chunk.block_type == "table", -item.chunk.page_no), reverse=True)
    return ranked[:limit]


def candidate_chunks_for_notice_document(
    pages: list[PdfPageText],
    *,
    limit_per_purpose: int = 4,
    max_chars: int = 1800,
) -> list[str]:
    selected: dict[str, RankedChunk] = {}
    for purpose, (query, keywords) in PURPOSE_QUERIES.items():
        for ranked in search_document_chunks(pages, query, keywords=keywords, limit=limit_per_purpose):
            selected.setdefault(ranked.chunk.chunk_id, ranked)

    if not selected:
        fallback_chunks = build_document_chunks(pages)[: limit_per_purpose * len(PURPOSE_QUERIES)]
        return [_format_chunk(chunk, score=0, matched_terms=(), max_chars=max_chars) for chunk in fallback_chunks]

    ranked_chunks = sorted(selected.values(), key=lambda item: item.score, reverse=True)
    return [
        _format_chunk(item.chunk, score=item.score, matched_terms=item.matched_terms, max_chars=max_chars)
        for item in ranked_chunks
    ]


def _rank_chunk(chunk: DocumentChunk, query_terms: tuple[str, ...]) -> RankedChunk:
    normalized_text = _normalize(chunk.text)
    matched_terms: list[str] = []
    score = 0.0
    for term in query_terms:
        normalized_term = _normalize(term)
        if not normalized_term:
            continue
        count = normalized_text.count(normalized_term)
        if count <= 0:
            continue
        matched_terms.append(term)
        score += 1 + min(count, 5) * 0.5

    if chunk.block_type == "table" and any(term in matched_terms for term in MONEY_TERMS):
        score += 2.0
    if re.search(r"\d{2,3}[A-Z]", chunk.text):
        score += 1.0
    if re.search(r"\d{1,3},\d{3}", chunk.text):
        score += 1.0
    return RankedChunk(chunk=chunk, score=round(score, 3), matched_terms=tuple(matched_terms))


def _extract_table_blocks(text: str) -> tuple[list[str], str]:
    table_blocks: list[str] = []
    remaining_lines: list[str] = []
    active_table: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("[table "):
            if active_table:
                table_blocks.append("\n".join(active_table))
            active_table = [stripped]
            continue
        if active_table:
            if not stripped:
                table_blocks.append("\n".join(active_table))
                active_table = []
                continue
            active_table.append(stripped)
            continue
        remaining_lines.append(line)
    if active_table:
        table_blocks.append("\n".join(active_table))
    return table_blocks, "\n".join(remaining_lines)


def _split_paragraphs(text: str) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text or "")
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", normalized) if paragraph.strip()]
    if paragraphs:
        return paragraphs
    return [normalized.strip()] if normalized.strip() else []


def _window_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    windows: list[str] = []
    start = 0
    step = max(max_chars - overlap_chars, max_chars // 2)
    while start < len(text):
        window = text[start : start + max_chars].strip()
        if window:
            windows.append(window)
        start += step
    return windows


def _terms(value: str) -> list[str]:
    return [term for term in re.split(r"[^0-9A-Za-z가-힣]+", value or "") if len(term) >= 2]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def _format_chunk(chunk: DocumentChunk, *, score: float, matched_terms: tuple[str, ...], max_chars: int) -> str:
    matched = ", ".join(matched_terms[:8]) if matched_terms else "fallback"
    header = f"[page {chunk.page_no} | {chunk.block_type} | score {score} | matched {matched}]"
    return f"{header}\n{chunk.text[:max_chars]}"
