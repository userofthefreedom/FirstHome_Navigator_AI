from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from apps.notice_docs.services.pdf_parser import PdfPageText


PRICE_SECTION_KEYWORDS = ("주택가격", "계약금", "중도금", "잔금", "공급금액", "분양가격")
UNIT_ROW_PATTERN = re.compile(
    r"(?P<unit>\d{2,3}[A-Z])"
    r"(?P<meta>.{0,40}?)"
    r"(?P<amounts>(?:\d{1,3}(?:,\d{3})+){3,12})"
)
DATE_PATTERN = re.compile(r"(?P<year>\d{2,4})[.년/-]\s*(?P<month>\d{1,2})[.월/-]\s*(?P<day>\d{1,2})")


@dataclass
class ExtractedSchedule:
    label: str
    due_date: date | None
    amount: int
    payment_type: str
    sequence: int
    evidence_text: str


@dataclass
class ExtractedUnitOption:
    unit_type: str
    exclusive_area_m2: float
    floor_group: str
    option_type: str
    base_price: int
    loan_amount: int
    balcony_extension_price: int
    confidence: float
    source_page: int
    source_text: str
    payment_schedules: list[ExtractedSchedule] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)


def extract_unit_options_from_pages(pages: list[PdfPageText]) -> list[ExtractedUnitOption]:
    options: list[ExtractedUnitOption] = []
    seen: set[tuple[str, str, str]] = set()

    for page in pages:
        if not _is_price_section(page.text):
            continue
        due_dates = _extract_middle_due_dates(page.text)
        compact_text = re.sub(r"\s+", "", page.text)
        for match in UNIT_ROW_PATTERN.finditer(compact_text):
            option = _option_from_match(page, match, due_dates)
            if option.base_price <= 0:
                continue
            key = (option.unit_type, option.floor_group, option.option_type)
            if key in seen:
                continue
            seen.add(key)
            options.append(option)
            if len(options) >= 20:
                return options

    return options


def extract_checklist_items(pages: list[PdfPageText]) -> list[dict[str, Any]]:
    categories = [
        ("homeless", "무주택 기준 확인", ("무주택", "세대구성", "주택소유")),
        ("income", "소득·자산 기준 확인", ("소득", "자산")),
        ("subscription", "청약통장 요건 확인", ("입주자저축", "청약통장", "납입")),
        ("residency", "지역 우선공급 확인", ("거주", "우선공급")),
    ]
    items: list[dict[str, Any]] = []
    for category, title, keywords in categories:
        evidence = _first_evidence(pages, keywords)
        if not evidence:
            continue
        items.append(
            {
                "category": category,
                "title": title,
                "condition_text": f"{title}은 공식 공고문 원문 기준으로 확인해야 합니다.",
                "evidence_text": evidence["text"],
                "confidence": 0.5,
                "page_no": evidence["page_no"],
            }
        )
    return items


def _option_from_match(page: PdfPageText, match: re.Match[str], due_dates: list[date]) -> ExtractedUnitOption:
    unit_type = match.group("unit")
    meta = match.group("meta")
    amounts = [_money_to_won(value) for value in re.findall(r"\d{1,3},\d{3}", match.group("amounts"))]
    base_price = amounts[0] if amounts else 0
    loan_amount = amounts[-1] if len(amounts) >= 2 else 0
    payment_amounts = amounts[1:-1] if len(amounts) >= 3 else []
    schedules = _payment_schedules(payment_amounts, due_dates, page)
    source_text = _source_snippet(page.text, match.group(0))

    return ExtractedUnitOption(
        unit_type=unit_type,
        exclusive_area_m2=_exclusive_area(unit_type),
        floor_group=_floor_group(meta),
        option_type="minus" if "마이너스" in meta else "basic",
        base_price=base_price,
        loan_amount=loan_amount,
        balcony_extension_price=0,
        confidence=0.78 if base_price and schedules else 0.55,
        source_page=page.page_no,
        source_text=source_text,
        payment_schedules=schedules,
        evidence=[
            {"field_path": "unit_option.base_price", "page_no": page.page_no, "source_text": source_text, "confidence": 0.78},
            {"field_path": "unit_option.payment_schedule", "page_no": page.page_no, "source_text": source_text, "confidence": 0.72},
        ],
    )


def _payment_schedules(amounts: list[int], due_dates: list[date], page: PdfPageText) -> list[ExtractedSchedule]:
    if not amounts:
        return []

    schedules: list[ExtractedSchedule] = [
        ExtractedSchedule(
            label="계약금",
            due_date=None,
            amount=amounts[0],
            payment_type="down_payment",
            sequence=1,
            evidence_text=_source_snippet(page.text, "계약금"),
        )
    ]

    middle_amounts = amounts[1:-1]
    for index, amount in enumerate(middle_amounts, start=1):
        due_date = due_dates[index - 1] if index - 1 < len(due_dates) else None
        schedules.append(
            ExtractedSchedule(
                label=f"중도금 {index}차",
                due_date=due_date,
                amount=amount,
                payment_type="middle_payment",
                sequence=index + 1,
                evidence_text=_source_snippet(page.text, f"{index}차 중도금"),
            )
        )

    if len(amounts) >= 2:
        schedules.append(
            ExtractedSchedule(
                label="잔금",
                due_date=None,
                amount=amounts[-1],
                payment_type="final_payment",
                sequence=len(schedules) + 1,
                evidence_text=_source_snippet(page.text, "잔금"),
            )
        )
    return schedules


def _extract_middle_due_dates(text: str) -> list[date]:
    result: list[date] = []
    for match in DATE_PATTERN.finditer(text):
        raw_year = int(match.group("year"))
        year = raw_year if raw_year >= 1000 else 2000 + raw_year
        try:
            result.append(date(year, int(match.group("month")), int(match.group("day"))))
        except ValueError:
            continue
    return list(dict.fromkeys(result))


def _money_to_won(value: str) -> int:
    amount = int(value.replace(",", ""))
    return amount if amount >= 10_000_000 else amount * 1000


def _exclusive_area(unit_type: str) -> float:
    match = re.match(r"(\d{2,3})", unit_type)
    return float(match.group(1)) if match else 0


def _floor_group(meta: str) -> str:
    floor = re.search(r"(최상층|\d{1,2}층|전체)", meta or "")
    return floor.group(1) if floor else "전체"


def _is_price_section(text: str) -> bool:
    return sum(1 for keyword in PRICE_SECTION_KEYWORDS if keyword in text) >= 3


def _first_evidence(pages: list[PdfPageText], keywords: tuple[str, ...]) -> dict[str, Any] | None:
    for page in pages:
        for keyword in keywords:
            if keyword not in page.text:
                continue
            return {"page_no": page.page_no, "text": _source_snippet(page.text, keyword)}
    return None


def _source_snippet(text: str, needle: str, *, radius: int = 90) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    index = compact.find(needle)
    if index < 0:
        return compact[: radius * 2]
    start = max(0, index - radius)
    end = min(len(compact), index + len(needle) + radius)
    return compact[start:end]
