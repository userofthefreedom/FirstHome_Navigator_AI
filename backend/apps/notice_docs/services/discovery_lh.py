from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from apps.notice_docs.models import NoticeDocument
from apps.notices.models import HousingNotice


LH_DOWNLOAD_PATH = "/lhapply/lhFile.do"
PREFERRED_NAME_KEYWORDS = ("입주자모집", "모집공고", "공고문")
LOW_PRIORITY_NAME_KEYWORDS = ("팸플릿", "브로셔", "위임장", "동의서", "견본주택", "안내문", "cad", "dwg")


@dataclass(frozen=True)
class DocumentCandidate:
    file_id: str
    file_name: str
    document_url: str
    source_url: str
    provider: str = "LH"
    priority: int = 0


def fetch_source_html(source_url: str, *, timeout: int = 10) -> str:
    response = requests.get(source_url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def parse_lh_document_candidates(source_html: str, source_url: str = "") -> list[DocumentCandidate]:
    candidates: list[DocumentCandidate] = []
    normalized_html = html.unescape(source_html or "")
    pattern = re.compile(
        r"fileDownLoad\('(?P<file_id>[^']+)'\);\s*\">\s*(?P<file_name>[^<]+?)\s*</a>",
        re.IGNORECASE,
    )

    for match in pattern.finditer(normalized_html):
        file_id = match.group("file_id").strip()
        file_name = _clean_file_name(match.group("file_name"))
        if not file_id or not file_name:
            continue

        document_url = urljoin(source_url, f"{LH_DOWNLOAD_PATH}?fileid={file_id}")
        candidates.append(
            DocumentCandidate(
                file_id=file_id,
                file_name=file_name,
                document_url=document_url,
                source_url=source_url,
                priority=_candidate_priority(file_name),
            )
        )

    return sorted(_dedupe_candidates(candidates), key=lambda item: item.priority, reverse=True)


def discover_documents_for_notice(notice: HousingNotice, *, source_html: str | None = None) -> list[NoticeDocument]:
    if source_html is None:
        if not notice.source_url:
            return []
        try:
            source_html = fetch_source_html(notice.source_url)
        except requests.RequestException as exc:
            return [_mark_discovery_failed(notice, str(exc))]

    candidates = parse_lh_document_candidates(source_html, notice.source_url)
    documents = [_save_candidate(notice, candidate) for candidate in candidates]
    return [document for document in documents if document is not None]


def _save_candidate(notice: HousingNotice, candidate: DocumentCandidate) -> NoticeDocument | None:
    defaults = {
        "provider": candidate.provider or notice.provider,
        "file_name": candidate.file_name,
        "document_url": candidate.document_url,
        "source_url": candidate.source_url or notice.source_url,
        "status": "discovered",
        "error_message": "",
    }
    if candidate.file_id:
        document, _created = NoticeDocument.objects.update_or_create(
            notice=notice,
            file_id=candidate.file_id,
            defaults=defaults,
        )
        return document

    document, _created = NoticeDocument.objects.update_or_create(
        notice=notice,
        document_url=candidate.document_url,
        defaults=defaults,
    )
    return document


def _mark_discovery_failed(notice: HousingNotice, message: str) -> NoticeDocument:
    document, _created = NoticeDocument.objects.get_or_create(
        notice=notice,
        document_url=notice.source_url or "",
        defaults={
            "provider": notice.provider,
            "file_name": _fallback_document_name(notice),
            "source_url": notice.source_url,
        },
    )
    document.status = "failed"
    document.error_message = message[:240]
    document.save(update_fields=["status", "error_message", "updated_at"])
    return document


def _candidate_priority(file_name: str) -> int:
    lower_name = file_name.lower()
    score = 0
    if lower_name.endswith(".pdf"):
        score += 50
    if lower_name.endswith(".hwp") or lower_name.endswith(".hwpx"):
        score += 15
    if any(keyword in file_name for keyword in PREFERRED_NAME_KEYWORDS):
        score += 40
    if any(keyword in lower_name for keyword in LOW_PRIORITY_NAME_KEYWORDS):
        score -= 30
    return score


def _clean_file_name(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _dedupe_candidates(candidates: list[DocumentCandidate]) -> list[DocumentCandidate]:
    seen: set[tuple[str, str]] = set()
    result: list[DocumentCandidate] = []
    for candidate in candidates:
        key = (candidate.file_id, candidate.file_name)
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _fallback_document_name(notice: HousingNotice) -> str:
    title = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", notice.title).strip("_")
    return f"{title[:80]}_official.html" if title else "official_notice.html"
