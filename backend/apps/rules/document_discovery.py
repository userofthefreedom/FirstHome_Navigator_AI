from __future__ import annotations


PREFERRED_NAME_KEYWORDS = ("입주자모집", "모집공고", "공고문")
EXACT_NOTICE_KEYWORDS = ("입주자모집공고문", "입주자 모집공고문", "모집공고문")
LOW_PRIORITY_NAME_KEYWORDS = (
    "팸플릿",
    "브로슈어",
    "위임장",
    "동의서",
    "견본주택",
    "안내문",
    "서식",
    "동호",
    "배치도",
    "평면도",
    "발코니",
    "옵션",
    "cad",
    "dwg",
)


def document_candidate_priority(file_name: str) -> int:
    lower_name = file_name.lower()
    score = 0
    if lower_name.endswith(".pdf"):
        score += 50
    if lower_name.endswith(".hwp") or lower_name.endswith(".hwpx"):
        score += 15
    if any(keyword in file_name for keyword in EXACT_NOTICE_KEYWORDS):
        score += 80
    if any(keyword in file_name for keyword in PREFERRED_NAME_KEYWORDS):
        score += 40
    if any(keyword in lower_name for keyword in LOW_PRIORITY_NAME_KEYWORDS):
        score -= 45
    return score
