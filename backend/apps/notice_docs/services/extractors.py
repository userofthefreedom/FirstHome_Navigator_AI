from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from apps.notice_docs.services.pdf_parser import PdfPageText


PRICE_SECTION_KEYWORDS = ("주택가격", "계약금", "중도금", "잔금", "공급금액", "분양가격")
TABLE_MARKER_PATTERN = re.compile(r"^\[table \d+\]$")
MAX_EXTRACTED_OPTIONS = 50
UNIT_ROW_PATTERN = re.compile(
    r"(?P<unit>\d{2,3}[A-Z])"
    r"(?P<meta>.{0,40}?)"
    r"(?P<amounts>(?:\d{1,3}(?:,\d{3})+){3,24})"
)
AREA_PREFIX_ROW_PATTERN = re.compile(
    r"(?P<block>B\d블록(?:\s*\([^)]*\))?)?\s*"
    r"0?\d{2,3}\.\d{4}[A-Z]?\s+"
    r"(?P<unit>\d{2,3}[A-Z])\s+"
    r"(?P<meta>.*?)"
    r"(?P<floor>최상층|\d{1,2}층|전체)\s+"
    r"(?P<count>\d+)\s+"
    r"(?P<amounts>\d{1,3}(?:,\d{3})+(?:\s+\d{1,3}(?:,\d{3})+){3,})"
)
DATE_PATTERN = re.compile(r"(?P<year>\d{2,4})[.년/-]\s*(?P<month>\d{1,2})[.월/-]\s*(?P<day>\d{1,2})")
LOAN_KEYWORDS = ("융자금", "대출금", "주택도시기금")


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
        table_options = _options_from_table_blocks(page)
        for option in table_options:
            if not _is_valid_base_price(option.base_price) or not _is_valid_exclusive_area(option.exclusive_area_m2):
                continue
            key = (option.unit_type, option.floor_group, option.option_type)
            if key in seen:
                continue
            seen.add(key)
            options.append(option)
            if len(options) >= MAX_EXTRACTED_OPTIONS:
                return options
        if table_options:
            continue
        due_dates = _extract_middle_due_dates(page.text)
        for option in _options_from_area_prefix_rows(page, due_dates):
            if not _is_valid_base_price(option.base_price) or not _is_valid_exclusive_area(option.exclusive_area_m2):
                continue
            key = (option.unit_type, option.floor_group, option.option_type)
            if key in seen:
                continue
            seen.add(key)
            options.append(option)
            if len(options) >= MAX_EXTRACTED_OPTIONS:
                return options
        compact_text = re.sub(r"\s+", "", page.text)
        for match in UNIT_ROW_PATTERN.finditer(compact_text):
            option = _option_from_match(page, match, due_dates)
            if not _is_valid_base_price(option.base_price) or not _is_valid_exclusive_area(option.exclusive_area_m2):
                continue
            key = (option.unit_type, option.floor_group, option.option_type)
            if key in seen:
                continue
            seen.add(key)
            options.append(option)
            if len(options) >= MAX_EXTRACTED_OPTIONS:
                return options

    return options


def _options_from_table_blocks(page: PdfPageText) -> list[ExtractedUnitOption]:
    options: list[ExtractedUnitOption] = []
    for block in _table_blocks(page.text):
        if not _is_payment_table(block):
            continue
        options.extend(_options_from_payment_table(page, block))
    return options


def _table_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    in_table = False
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if TABLE_MARKER_PATTERN.match(line):
            if current:
                blocks.append(current)
            current = []
            in_table = True
            continue
        if in_table:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _is_payment_table(block: list[str]) -> bool:
    header = " ".join(block[:4])
    if "계약금" not in header:
        return False
    if "발코니 확장 공사비" in header or "추가선택품목" in header:
        return False
    price_keywords = ("공급금액", "주택가격", "분양가격", "공급가격", "합계")
    unit_keywords = ("주택형", "주택타입", "타입")
    return any(keyword in header for keyword in price_keywords) and any(keyword in header for keyword in unit_keywords)


def _options_from_payment_table(page: PdfPageText, block: list[str]) -> list[ExtractedUnitOption]:
    options: list[ExtractedUnitOption] = []
    header_rows: list[str] = []
    data_rows: list[str] = []
    for row in block:
        if len(row) > 500:
            continue
        if _row_money_values(row):
            data_rows.append(row)
        else:
            header_rows.append(row)

    header_text = " ".join(header_rows[:4])
    active_unit = ""
    for row in data_rows:
        parsed = _parse_payment_table_row(page, row, header_text, active_unit)
        if parsed is None:
            continue
        option, active_unit = parsed
        options.append(option)
    return options


def _parse_payment_table_row(
    page: PdfPageText,
    row: str,
    header_text: str,
    active_unit: str,
) -> tuple[ExtractedUnitOption, str] | None:
    amounts = _row_money_values(row)
    if len(amounts) < 3:
        return None

    row_unit = _row_unit_type(row)
    unit_type = row_unit or active_unit
    if not unit_type:
        return None

    floor_group = _floor_group(row)
    schedules, base_price, loan_amount, balcony_extension_price = _schedules_from_table_amounts(
        amounts,
        header_text,
        row,
        page.text,
    )
    if base_price <= 0 or not schedules:
        return None

    option = ExtractedUnitOption(
        unit_type=unit_type,
        exclusive_area_m2=_exclusive_area(unit_type),
        floor_group=floor_group,
        option_type=_option_type_from_text(f"{header_text} {row}"),
        base_price=base_price,
        loan_amount=loan_amount,
        balcony_extension_price=balcony_extension_price,
        confidence=0.88,
        source_page=page.page_no,
        source_text=row,
        payment_schedules=schedules,
        evidence=[
            {"field_path": "unit_option.base_price", "page_no": page.page_no, "source_text": row, "confidence": 0.88},
            {"field_path": "unit_option.payment_schedule", "page_no": page.page_no, "source_text": row, "confidence": 0.84},
        ],
    )
    return option, unit_type


def _schedules_from_table_amounts(
    amounts: list[int],
    header_text: str,
    row: str,
    page_text: str,
) -> tuple[list[ExtractedSchedule], int, int, int]:
    if "할부금" in header_text and "입주잔금" in header_text and len(amounts) >= 6:
        base_price = amounts[0]
        balcony_extension_price = amounts[1]
        loan_amount = amounts[4]
        rows = [
            ("계약금", amounts[2], "down_payment"),
            ("입주잔금", amounts[3], "final_payment"),
            ("할부금", amounts[5], "installment_payment"),
        ]
        return _named_schedules(rows, row), base_price, loan_amount, balcony_extension_price

    if "할부금" in header_text and "합계" in header_text and len(amounts) >= 4:
        base_price = amounts[-1]
        rows = [
            ("계약금", amounts[0], "down_payment"),
            ("잔금", amounts[1], "final_payment"),
            ("할부금", amounts[2], "installment_payment"),
        ]
        return _named_schedules(rows, row), base_price, 0, 0

    base_price = amounts[0]
    loan_amount = amounts[-1] if any(keyword in header_text for keyword in LOAN_KEYWORDS) and len(amounts) >= 4 else 0
    payment_amounts = amounts[1:-1] if loan_amount else amounts[1:]
    if not payment_amounts:
        return [], base_price, loan_amount, 0

    middle_count = len(re.findall(r"\d+차", header_text))
    if middle_count == 0 and "중도금" in header_text and len(payment_amounts) >= 3:
        middle_count = len(payment_amounts) - 2
    if middle_count == 0 and "중도금" in header_text and len(payment_amounts) >= 2:
        middle_count = 1

    schedules = [
        ExtractedSchedule(
            label="계약금",
            due_date=None,
            amount=payment_amounts[0],
            payment_type="down_payment",
            sequence=1,
            evidence_text=row,
        )
    ]
    due_dates = _extract_middle_due_dates(header_text) or _extract_middle_due_dates(page_text)
    middle_amounts = payment_amounts[1 : 1 + middle_count]
    for index, amount in enumerate(middle_amounts, start=1):
        schedules.append(
            ExtractedSchedule(
                label=f"중도금 {index}차",
                due_date=due_dates[index - 1] if index - 1 < len(due_dates) else None,
                amount=amount,
                payment_type="middle_payment",
                sequence=len(schedules) + 1,
                evidence_text=row,
            )
        )
    final_index = 1 + middle_count
    if final_index < len(payment_amounts):
        schedules.append(
            ExtractedSchedule(
                label="잔금",
                due_date=None,
                amount=payment_amounts[final_index],
                payment_type="final_payment",
                sequence=len(schedules) + 1,
                evidence_text=row,
            )
        )
    return schedules, base_price, loan_amount, 0


def _named_schedules(rows: list[tuple[str, int, str]], evidence_text: str) -> list[ExtractedSchedule]:
    return [
        ExtractedSchedule(
            label=label,
            due_date=None,
            amount=amount,
            payment_type=payment_type,
            sequence=index,
            evidence_text=evidence_text,
        )
        for index, (label, amount, payment_type) in enumerate(rows, start=1)
        if amount >= 0
    ]


def _row_money_values(row: str) -> list[int]:
    return [_money_to_won(value) for value in re.findall(r"\d{1,3}(?:,\d{3})+", row)]


def _row_unit_type(row: str) -> str:
    display_units = [
        value
        for value in re.findall(r"\b\d{2,3}[A-Z]{1,2}\b", row)
        if not value.endswith("층")
    ]
    if display_units:
        return _normalize_unit_type(display_units[0])
    area_code = re.search(r"\b0?\d{2,3}\.\d{4}[A-Z]?\b", row)
    if area_code:
        return _normalize_unit_type(area_code.group(0))
    return ""


def _option_type_from_text(text: str) -> str:
    if "사전청약" in text:
        return "pre_subscription"
    if "계약금(5%)" in text and "중도금(30%)" in text:
        return "pre_subscription"
    if "일반 당첨자" in text or "특별공급" in text or "일반공급" in text:
        return "general_supply"
    if "계약금(10%)" in text and "중도금(60%)" in text:
        return "general_supply"
    return "minus" if "마이너스" in text else "basic"


def _options_from_area_prefix_rows(page: PdfPageText, due_dates: list[date]) -> list[ExtractedUnitOption]:
    options: list[ExtractedUnitOption] = []
    active_block = ""
    for raw_line in page.text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        block_match = re.search(r"B\d블록", line)
        if block_match:
            active_block = block_match.group(0)
        for match in AREA_PREFIX_ROW_PATTERN.finditer(line):
            block = _clean_block_label(match.group("block") or active_block)
            option = _option_from_area_prefix_match(page, match, due_dates, line, block)
            options.append(option)
    return options


def _option_from_area_prefix_match(
    page: PdfPageText,
    match: re.Match[str],
    due_dates: list[date],
    source_text: str,
    block: str,
) -> ExtractedUnitOption:
    unit_type = _normalize_unit_type(match.group("unit"))
    meta = match.group("meta")
    amounts = [_money_to_won(value) for value in re.findall(r"\d{1,3},\d{3}(?:,\d{3})?", match.group("amounts"))]
    base_price, payment_amounts, loan_amount = _split_price_amounts(amounts, page.text)
    schedules = _payment_schedules(payment_amounts, due_dates, page)
    floor_group = " ".join(part for part in [block, match.group("floor")] if part).strip() or _floor_group(meta)

    return ExtractedUnitOption(
        unit_type=unit_type,
        exclusive_area_m2=_exclusive_area(unit_type),
        floor_group=floor_group,
        option_type="minus" if "마이너스" in meta else "basic",
        base_price=base_price,
        loan_amount=loan_amount,
        balcony_extension_price=0,
        confidence=0.82 if base_price and schedules else 0.58,
        source_page=page.page_no,
        source_text=source_text,
        payment_schedules=schedules,
        evidence=[
            {"field_path": "unit_option.base_price", "page_no": page.page_no, "source_text": source_text, "confidence": 0.82},
            {"field_path": "unit_option.payment_schedule", "page_no": page.page_no, "source_text": source_text, "confidence": 0.74},
        ],
    )


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
    unit_type = _normalize_unit_type(match.group("unit"))
    meta = match.group("meta")
    amounts = [_money_to_won(value) for value in re.findall(r"\d{1,3},\d{3}", match.group("amounts"))]
    base_price, payment_amounts, loan_amount = _split_price_amounts(amounts, page.text)
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


def _split_price_amounts(amounts: list[int], context_text: str) -> tuple[int, list[int], int]:
    if not amounts:
        return 0, [], 0

    base_price = amounts[0]
    remaining = amounts[1:]
    if not remaining:
        return base_price, [], 0

    has_loan_column = any(keyword in context_text for keyword in LOAN_KEYWORDS)
    if has_loan_column and len(remaining) >= 3:
        return base_price, remaining[:-1], remaining[-1]
    return base_price, remaining, 0


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


def _normalize_unit_type(unit_type: str) -> str:
    area_code = re.match(r"0*(\d{2,3})\.\d{4}([A-Z])?", unit_type or "")
    if area_code:
        suffix = area_code.group(2) or "A"
        return f"{int(area_code.group(1))}{suffix}"
    match = re.match(r"0*(\d{2,3})([A-Z])", unit_type or "")
    return f"{int(match.group(1))}{match.group(2)}" if match else unit_type


def _clean_block_label(value: str) -> str:
    match = re.search(r"B\d블록", value or "")
    return match.group(0) if match else ""


def _is_valid_exclusive_area(value: float) -> bool:
    return 20 <= value <= 120


def _is_valid_base_price(value: int) -> bool:
    return value >= 100_000_000


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
