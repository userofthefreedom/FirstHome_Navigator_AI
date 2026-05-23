from __future__ import annotations

from typing import Any

from apps.ai_coach.models import AiChatLog
from apps.ai_coach.services.ai_client import AiClientError, chat_completion, llm_enabled
from apps.ai_coach.services.safety_filter import sanitize_actions, sanitize_reply, sanitize_summary, safety_flags
from apps.fixture_store import default_profile, find_notice
from apps.funding.services.calculator import funding_plan
from apps.notice_docs.services.schemas import COACH_CHAT_SCHEMA
from apps.recommendations.services.ranking import calculate_score


def coach_summary(notice_id: int, profile: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile)
    if notice is None or plan is None:
        return None

    recommendation = calculate_score(notice, profile)
    summary = {
        "source": "template_fallback",
        "summary": (
            f"{notice['title']}은(는) {notice['region']} 희망 지역과 {notice['supply_type']} 조건에 맞는 후보입니다. "
            f"현재 추천 점수는 {recommendation['total_score']}점이고 계약금 기준 부족액은 {plan['shortfall']:,}원입니다. "
            f"월 {plan['monthly_target']:,}원 정도를 준비하는 계획을 세우되, 자격과 금액은 공식 공고문에서 다시 확인하세요."
        ),
        "todo_this_week": [
            "주민등록등본, 소득금액증명, 청약통장 가입확인서 발급 가능 여부를 확인하세요.",
            f"{notice['provider']} 또는 공식 청약 사이트에서 무주택, 소득, 자산 기준을 확인하세요.",
            "계약금으로 쓸 현금과 생활비로 남길 금액을 분리해 관리하세요.",
        ],
        "official_checklist": [
            "무주택 및 세대 구성 기준",
            "소득, 자산, 청약통장 가입 인정 기준",
            "접수 마감일, 계약일, 분양가와 납부 일정",
        ],
        "warning": "추천 결과는 공고문 분석과 입력 프로필 기반의 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다.",
    }
    return sanitize_summary(summary)


def coach_chat(
    notice_id: int,
    message: str,
    profile: dict[str, Any] | None = None,
    *,
    option_id: int | None = None,
) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile, option_id=option_id)
    if notice is None or plan is None:
        return None

    llm_response = _coach_chat_with_llm(notice, plan, profile, message)
    if llm_response:
        return llm_response

    normalized = message.replace(" ", "").lower()
    if any(keyword in normalized for keyword in ["부족", "계약금", "돈", "자금", "얼마"]):
        reply = _funding_reply(notice, plan)
        actions = [
            "계약금 납부일과 금액을 공식 공고문에서 다시 확인하세요.",
            "보유 현금 중 생활비로 남길 금액을 먼저 분리하세요.",
            "월 저축 가능액으로 부족액 준비 기간을 다시 계산하세요.",
        ]
    elif any(keyword in normalized for keyword in ["일정", "날짜", "마감", "언제"]):
        reply = _schedule_reply(notice, plan)
        actions = [
            "접수 마감일과 계약일을 캘린더에 등록하세요.",
            "중도금 회차별 납부일이 변경될 수 있는지 공고문 유의사항을 확인하세요.",
            "당첨자 발표 이후 서류 제출 기간을 함께 확인하세요.",
        ]
    elif any(keyword in normalized for keyword in ["pdf", "공고문", "서류", "확인", "문장"]):
        reply = _document_reply(notice, plan)
        actions = [
            "공식 공고문 PDF의 주택가격표와 납부조건 표를 확인하세요.",
            "무주택, 소득, 자산, 청약통장 기준은 별도로 체크하세요.",
            "화면의 분석 결과와 원문이 다르면 원문을 우선하세요.",
        ]
    else:
        reply = _general_reply(notice, plan)
        actions = [
            "추천 상세에서 주택형 옵션과 납부 일정을 확인하세요.",
            "자금 로드맵에서 부족액과 월 준비 목표를 확인하세요.",
            "실제 신청 전 공식 공고문 원문을 확인하세요.",
        ]

    response = {
        "source": "template_fallback",
        "notice_id": notice_id,
        "notice_title": notice["title"],
        "option_id": plan.get("option_id"),
        "reply": sanitize_reply(reply),
        "suggested_actions": sanitize_actions(actions),
        "context_refs": [
            {"type": "notice", "notice_id": notice_id},
            {"type": "funding_plan", "notice_id": notice_id, "option_id": plan.get("option_id")},
        ],
    }
    _save_chat_log(response, message, provider="template", safety_flags=safety_flags(reply))
    return response


def _coach_chat_with_llm(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    message: str,
) -> dict[str, Any] | None:
    if not llm_enabled("chat"):
        return None

    context = _chat_context(notice, plan, profile)
    try:
        ai_response = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 FirstHome Navigator AI의 청약 준비 코치입니다. "
                        "답변은 한국어 2~3문장, 350자 이내로 작성합니다. "
                        "금액과 날짜가 있으면 먼저 말하고, 불확실한 일반론이나 보장 표현은 피합니다. "
                        "당첨, 신청 가능, 자격 충족, 대출 승인 같은 확정 표현은 금지합니다. "
                        "반드시 '공식 공고문 확인이 필요합니다'라는 취지의 문장을 포함합니다."
                    ),
                },
                {"role": "user", "content": f"컨텍스트:\n{context}\n\n질문:\n{message}"},
            ],
            response_schema=COACH_CHAT_SCHEMA,
            temperature=0.2,
        )
    except AiClientError as exc:
        _save_chat_log(
            {
                "notice_id": notice["id"],
                "option_id": plan.get("option_id"),
                "reply": "",
                "suggested_actions": [],
                "context_refs": [],
            },
            message,
            provider="llm_failed",
            error_message=str(exc),
        )
        return None

    payload = ai_response.parsed_json or {}
    response = {
        "source": "llm",
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "option_id": plan.get("option_id"),
        "reply": sanitize_reply(str(payload.get("reply", ""))),
        "suggested_actions": sanitize_actions([str(action) for action in payload.get("suggested_actions", [])]),
        "context_refs": payload.get("context_refs", []),
    }
    if not response["reply"]:
        return None
    _save_chat_log(
        response,
        message,
        provider=ai_response.provider,
        model_name=ai_response.model,
        raw_response=ai_response.raw_response,
        safety_flags=safety_flags(str(payload.get("reply", ""))),
    )
    return response


def _funding_reply(notice: dict[str, Any], plan: dict[str, Any]) -> str:
    unit = _unit_label(plan)
    return (
        f"{notice['title']} {unit} 기준 계약금은 약 {plan['down_payment']:,}원입니다. "
        f"현재 준비 가능한 현금 {plan['available_cash']:,}원을 반영하면 부족액은 약 {plan['shortfall']:,}원이고 "
        f"{plan['months_until_contract']}개월 기준 월 {plan['monthly_target']:,}원 정도를 준비해야 합니다. "
        "이 계산은 참고용이며 실제 납부 조건은 공식 공고문 확인이 필요합니다."
    )


def _schedule_reply(notice: dict[str, Any], plan: dict[str, Any]) -> str:
    timeline = plan.get("timeline") or []
    payable_rows = [row for row in timeline if int(row.get("amount") or 0) > 0]
    first_payment = payable_rows[0] if payable_rows else None
    if first_payment:
        return (
            f"{notice['title']}의 첫 납부 항목은 {first_payment['label']}이고 "
            f"금액은 약 {int(first_payment['amount']):,}원입니다. 날짜는 {first_payment.get('date') or '공식 확인 필요'}로 표시되어 있습니다. "
            "중도금 일정은 기관 안내에 따라 달라질 수 있어 공식 공고문 확인이 필요합니다."
        )
    return (
        f"{notice['title']}은 접수 마감 {notice['application_deadline']}, 당첨자 발표 {notice['winner_date']}, "
        f"계약일 {notice['contract_date']} 기준으로 관리하면 됩니다. 납부 일정은 공식 공고문 확인이 필요합니다."
    )


def _document_reply(notice: dict[str, Any], plan: dict[str, Any]) -> str:
    source = "공식 공고문 추출 일정" if plan.get("schedule_source") == "payment_schedule" else "공고 대표값"
    return (
        f"현재 답변은 {source} 기준입니다. 공식 공고문에서는 주택가격표, 계약금/중도금/잔금 납부조건, "
        "무주택·소득·자산·청약통장 기준을 우선 확인하세요. 분석 결과는 참고용이며 원문과 다르면 원문을 우선해야 합니다."
    )


def _general_reply(notice: dict[str, Any], plan: dict[str, Any]) -> str:
    return (
        f"{notice['title']}은 {notice['region']} 지역의 {notice['supply_type']} 후보입니다. "
        f"현재 자금 로드맵상 부족액은 약 {plan['shortfall']:,}원입니다. "
        "추천 점수와 AI 답변은 참고용이며 신청 가능 여부와 납부 조건은 공식 공고문 확인이 필요합니다."
    )


def _unit_label(plan: dict[str, Any]) -> str:
    if not plan.get("option_id"):
        return ""
    return f"{plan.get('unit_type', '')} {plan.get('floor_group', '')}".strip()


def _chat_context(notice: dict[str, Any], plan: dict[str, Any], profile: dict[str, Any]) -> str:
    timeline = "\n".join(
        f"- {row.get('label')}: {row.get('date')} / {int(row.get('amount') or 0):,}원"
        for row in plan.get("timeline", [])[:8]
    )
    return (
        f"공고: {notice['title']}\n"
        f"지역/공급유형: {notice['region']} {notice['district']} / {notice['supply_type']}\n"
        f"선택 옵션: {plan.get('unit_type', '공고 대표값')} {plan.get('floor_group', '')}\n"
        f"분양가: {plan.get('price', 0):,}원\n"
        f"계약금: {plan.get('down_payment', 0):,}원\n"
        f"부족액: {plan.get('shortfall', 0):,}원\n"
        f"월 준비 목표: {plan.get('monthly_target', 0):,}원\n"
        f"사용자 자산: {int(profile.get('asset') or 0):,}원\n"
        f"월 저축 가능액: {int(profile.get('monthly_saving') or 0):,}원\n"
        f"타임라인:\n{timeline}"
    )


def _save_chat_log(
    response: dict[str, Any],
    question: str,
    *,
    provider: str,
    model_name: str = "",
    raw_response: dict[str, Any] | None = None,
    error_message: str = "",
    safety_flags: list[str] | None = None,
) -> None:
    AiChatLog.objects.create(
        notice_id=response.get("notice_id"),
        option_id=response.get("option_id"),
        question=question,
        answer=str(response.get("reply", "")),
        provider=provider,
        model_name=model_name,
        source_refs=response.get("context_refs", []),
        safety_flags=safety_flags or [],
        raw_response=raw_response or {},
        error_message=error_message,
    )
