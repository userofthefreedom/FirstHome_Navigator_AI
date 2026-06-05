from __future__ import annotations

import hashlib
import json
from time import perf_counter
from typing import Any

from django.contrib.auth.models import AnonymousUser

from apps.ai_coach.models import AiChatLog, AiCoachPlan
from apps.ai_coach.services.ai_client import AiClientError, chat_completion, llm_enabled
from apps.ai_coach.services.safety_filter import sanitize_actions, sanitize_reply, sanitize_summary, safety_flags
from apps.fixture_store import default_profile, find_notice
from apps.funding.services.calculator import funding_plan
from apps.notice_docs.services.schemas import COACH_CHAT_SCHEMA, COACH_SUMMARY_SCHEMA
from apps.recommendations.services.ranking import calculate_score


def coach_summary(
    notice_id: int,
    profile: dict[str, Any] | None = None,
    *,
    option_id: int | None = None,
    user: Any = None,
    allow_llm: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    profile = profile or default_profile()
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile, option_id=option_id)
    if notice is None or plan is None:
        return None

    recommendation = calculate_score(notice, profile)
    official_context = _official_context(notice_id, plan.get("option_id"))
    is_fixture = _is_fixture_notice(notice) or bool(official_context.get("is_fixture"))
    plan_input_hash = _coach_plan_input_hash(notice, plan, profile, official_context)
    authenticated_user = user if _is_authenticated_user(user) else None

    if authenticated_user and not force_refresh:
        cached = AiCoachPlan.objects.filter(
            user=authenticated_user,
            notice_id=notice_id,
            option_id=int(plan.get("option_id") or 0),
            input_hash=plan_input_hash,
        ).first()
        if cached:
            cached_payload = dict(cached.payload or {})
            cached_payload["source"] = "cached_llm" if cached_payload.get("source") == "llm" else cached_payload.get("source", "cached")
            cached_payload["cached_at"] = cached.updated_at.isoformat()
            cached_payload["requires_login"] = False
            cached_payload.setdefault("is_fixture", is_fixture)
            return cached_payload

    llm_response = None
    if allow_llm:
        llm_response = _coach_summary_with_llm(
            notice,
            plan,
            profile,
            recommendation,
            official_context=official_context,
        )
    if llm_response:
        llm_response["requires_login"] = False
        llm_response["is_fixture"] = is_fixture
        if authenticated_user:
            AiCoachPlan.objects.update_or_create(
                user=authenticated_user,
                notice_id=notice_id,
                option_id=int(plan.get("option_id") or 0),
                input_hash=plan_input_hash,
                defaults={
                    "payload": llm_response,
                    "provider": "llm",
                    "model_name": str(llm_response.get("model_name", "")),
                },
            )
        return llm_response

    summary = {
        "source": "login_required_sample" if not allow_llm else "template_fallback",
        "requires_login": not allow_llm,
        "is_fixture": is_fixture,
        "notice_id": notice_id,
        "notice_title": notice["title"],
        "option_id": plan.get("option_id"),
        "summary": (
            f"{notice['title']}은(는) {notice['region']} 희망 지역과 {notice['supply_type']} 조건에 맞는 후보입니다. "
            f"현재 추천 점수는 {recommendation['total_score']}점이고 계약금 기준 부족액은 {plan['shortfall']:,}원입니다. "
            f"월 {plan['monthly_target']:,}원 정도를 준비하는 계획을 세우되, 자격과 금액은 {'fixture 구조화 데이터 기준의 참고값으로만 보세요.' if is_fixture else '공식 공고문에서 다시 확인하세요.'}"
        ),
        "todo_this_week": (
            [
                f"{plan.get('unit_type', '선택 주택형')} {plan.get('floor_group', '')} 기준 계약금 부족액 {plan['shortfall']:,}원을 월 {plan['monthly_target']:,}원 준비 계획으로 바꾸세요.",
                "이 후보는 fixture라 실제 공식 PDF 확인이 불가하다는 점을 먼저 표시하세요.",
                "fixture 제출서류 후보와 자격 후보를 예시 체크리스트로만 검토하세요.",
                "지역우선, 특별공급, 선택품목, 감액 조건은 fixture 구조화 데이터 기준의 판단거리로 정리하세요.",
                "계약금, 중도금, 잔금, 융자금 일정을 캘린더에 나눠 등록하세요.",
            ]
            if is_fixture
            else [
                f"{plan.get('unit_type', '선택 주택형')} {plan.get('floor_group', '')} 기준 계약금 부족액 {plan['shortfall']:,}원을 월 {plan['monthly_target']:,}원 준비 계획으로 바꾸세요.",
                "무주택, 소득·자산, 청약통장 기준을 공식 공고문 페이지 기준으로 한 번에 확인하세요.",
                "당첨자 제출서류와 주민등록표등본 등 발급 서류의 준비 순서를 정하세요.",
                "공고문 세부 조건 중 지역우선, 특별공급, 선택품목, 감액 조건처럼 본인에게 적용될 항목을 따로 표시하세요.",
                "계약금, 중도금, 잔금, 융자금 일정을 캘린더에 나눠 등록하세요.",
            ]
        ),
        "official_checklist": (
            ["Fixture 주택형·분양가 데이터", "Fixture 납부 일정 데이터", "Fixture 자격·서류 후보"]
            if is_fixture
            else [
                "무주택 및 세대 구성 기준",
                "소득, 자산, 청약통장 가입 인정 기준",
                "접수 마감일, 계약일, 분양가와 납부 일정",
            ]
        ),
        "deep_review_items": [
            {
                "title": "지역우선 또는 거주기간 기준",
                "body": "공고문에 거주기간이나 지역우선 물량 배정 기준이 있으면 현재 거주지와 전입일을 대조해야 합니다.",
                "why_it_matters": "같은 공고라도 거주기간에 따라 우선순위나 배정 물량이 달라질 수 있습니다.",
            },
            {
                "title": "특별공급 세부 자격",
                "body": "다자녀, 신혼부부, 생애최초 등 특별공급 기준은 유형별로 소득, 자산, 세대 구성 조건이 다를 수 있습니다.",
                "why_it_matters": "큰 공급유형만으로는 실제 신청 가능 유형을 확정할 수 없습니다.",
            },
            {
                "title": "선택품목과 감액 조건",
                "body": "추가 선택품목, 미선택 시 감액, 별도계약 항목이 있으면 실제 준비 금액과 계약 판단에 반영해야 합니다.",
                "why_it_matters": "구조화된 분양가 외 비용이나 감액 조건이 자금 계획을 바꿀 수 있습니다.",
            },
        ],
        "decision_points": [
            {
                "title": "선택 옵션의 자금 부담 확정",
                "body": "이미 선택한 주택형 기준으로 계약금, 중도금, 잔금, 융자금 흐름을 공식 공고문과 비교하세요.",
                "cta": "옵션 자금 보기",
            },
            {
                "title": "공고문 세부 조건 확인",
                "body": "지역우선, 특별공급, 선택품목, 감액 조건처럼 시스템이 완전히 판단하기 어려운 항목을 공식 원문과 대조하세요.",
                "cta": "공식 근거 보기",
            },
            {
                "title": "서류 준비 순서 정리",
                "body": "당첨자 제출서류 중 발급 시간이 걸리는 서류부터 미리 확인하세요.",
                "cta": "공식 근거 보기",
            },
        ],
        "warning": (
            "이 후보는 실제 PDF가 없는 fixture 보강 데이터이므로 공식 PDF 확인과 공식 원문 확인 항목은 제공되지 않습니다. 추천 결과는 발표용 참고 정보입니다."
            if is_fixture
            else "추천 결과는 공고문 분석과 입력 프로필 기반의 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다."
        ),
        "context_refs": official_context["refs"],
    }
    if not allow_llm:
        summary["login_message"] = (
            "회원가입 또는 로그인하면 fixture 구조화 데이터와 선택 주택형을 바탕으로 OpenAI LLM 예시 코칭을 받을 수 있습니다. fixture에는 실제 공식 PDF 원문이 연결되어 있지 않습니다."
            if is_fixture
            else "회원가입 또는 로그인하면 선택한 공고와 주택형, 공식 PDF 분석 근거를 바탕으로 OpenAI LLM 맞춤 코칭을 받을 수 있습니다."
        )
    response = sanitize_summary(summary)
    response["decision_points"] = _sanitize_decision_points(response.get("decision_points", []))
    return response


def _coach_summary_with_llm(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    official_context: dict[str, Any],
) -> dict[str, Any] | None:
    if not llm_enabled("chat"):
        return None

    context = _coach_summary_context(notice, plan, profile, recommendation, official_context=official_context)
    source_instruction = (
        "이 공고는 실제 공식 PDF가 없는 fixture 보강 데이터입니다. 공식 PDF 원문, 실제 페이지 확인, 공식 출처 확인을 완료한 것처럼 말하지 마세요. "
        "fixture 구조화 데이터 기준의 예시 분석이라고 명확히 표현하고, 공식 원문 확인이 필요한 영역은 'fixture에는 실제 PDF가 없어 확인 불가'라고 쓰세요. "
        if official_context.get("is_fixture")
        else "실제 공고문 분석 근거가 제공된 경우 그 근거를 우선하되, 최종 신청 전 공식 공고문 원문 확인이 필요하다고 쓰세요. "
    )
    started_at = perf_counter()
    try:
        ai_response = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 FirstHome Navigator AI의 청약 준비 코치입니다. "
                        "사용자가 앞으로 무엇을 해야 하고 어떤 후보를 우선 검토할지 정리합니다. "
                        "사용자가 option_id가 있는 선택 주택형에서 들어온 경우, 이미 공고와 옵션을 선택한 상태입니다. 후보를 하나 정하라는 조언은 하지 마세요. "
                        "모든 조언은 반드시 제공된 특정 공고, 선택 주택형, 계약금 부족액, 월 준비 목표, 마감일 중 하나 이상을 반영해야 합니다. "
                        "모든 공고와 모든 사용자에게 통하는 일반 조언만 쓰지 마세요. "
                        f"{source_instruction}"
                        "사용자가 말한 발코니는 예시일 뿐입니다. 발코니만 반복하지 말고 지역우선 물량, 거주기간, 특별공급, 다자녀/신혼/생애최초 조건, 선택품목, 미선택 감액, 별도계약, 전매/거주의무, 서류, 납부 유의사항 등 공고문에서 발견되는 다양한 판단거리를 우선순위로 뽑으세요. "
                        "추가 선택품목 금액이 0원으로 제공되면 무료라고 단정하지 말고, 구조화된 금액이 아직 없으므로 공식 공고문 원문 확인이 필요하다고 표현하세요. "
                        "제출서류는 컨텍스트의 제출서류 후보를 가능한 한 반영하고, 신분증/등본 같은 일부 서류만 반복하지 마세요. "
                        "답변은 한국어로 작성하고, 청약 신청 가능 여부, 당첨, 정책 수급, 대출 승인을 확정하지 않습니다. "
                        "금액과 일정은 참고 계산이며 공식 공고문 확인이 필요하다는 취지를 warning에 포함합니다. "
                        "todo_this_week는 4~5개이며 중복되는 자격 확인을 여러 항목으로 쪼개지 말고, 자금 계획, 공식 자격 기준, 제출서류, 공고문 세부 판단거리, 납부 일정 중 서로 다른 영역으로 나눕니다. "
                        "official_checklist는 3~5개이며 가능하면 공고문 페이지나 확인 항목명을 포함합니다. "
                        "deep_review_items는 4~6개이며 사용자가 룰 기반 화면만 보고 놓칠 수 있는 공고문 세부 판단거리를 작성합니다. 각 항목은 무엇을 확인해야 하는지와 왜 중요한지를 구체적으로 설명합니다. "
                        "decision_points는 정확히 3개이며 이 사용자가 왜 그 선택을 해야 하는지 구체 숫자와 함께 작성합니다."
                    ),
                },
                {"role": "user", "content": f"컨텍스트:\n{context}\n\n이 사용자의 청약 준비 플랜을 구조화하세요."},
            ],
            response_schema=COACH_SUMMARY_SCHEMA,
            temperature=0.25,
        )
        latency_ms = round((perf_counter() - started_at) * 1000)
    except AiClientError as exc:
        latency_ms = round((perf_counter() - started_at) * 1000)
        _save_chat_log(
            {
                "notice_id": notice["id"],
                "option_id": plan.get("option_id"),
                "summary": "",
                "context_refs": official_context["refs"],
            },
            "AI Coach summary",
            provider="llm_failed",
            error_message=str(exc),
            latency_ms=latency_ms,
        )
        return None

    payload = ai_response.parsed_json or {}
    is_fixture = bool(official_context.get("is_fixture"))
    response = {
        "source": "llm",
        "is_fixture": is_fixture,
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "option_id": plan.get("option_id"),
        "model_name": ai_response.model,
        "summary": sanitize_reply(str(payload.get("summary", ""))),
        "todo_this_week": sanitize_actions([str(action) for action in payload.get("todo_this_week", [])], limit=5),
        "official_checklist": sanitize_actions([str(item) for item in payload.get("official_checklist", [])], limit=5),
        "deep_review_items": _sanitize_deep_review_items(payload.get("deep_review_items", [])),
        "decision_points": _sanitize_decision_points(payload.get("decision_points", [])),
        "warning": sanitize_reply(
            "이 후보는 실제 공식 PDF가 없는 fixture 보강 데이터입니다. 공식 PDF 확인은 fixture라 불가하며, LLM 분석은 fixture 구조화 데이터 기준의 예시이고 실제 신청 근거가 아닙니다."
            if is_fixture
            else str(payload.get("warning", ""))
        ),
        "context_refs": official_context["refs"],
    }
    if not response["summary"]:
        return None
    _save_chat_log(
        response,
        "AI Coach summary",
        provider=ai_response.provider,
        model_name=ai_response.model,
        raw_response=ai_response.raw_response,
        safety_flags=safety_flags(" ".join([response["summary"], response["warning"]])),
        latency_ms=latency_ms,
    )
    return response


def coach_chat(
    notice_id: int,
    message: str,
    profile: dict[str, Any] | None = None,
    *,
    option_id: int | None = None,
    page_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    profile = profile or default_profile()
    page_context = page_context or {}
    notice = find_notice(notice_id)
    plan = funding_plan(notice_id, profile, option_id=option_id)
    if notice is None or plan is None:
        return None

    official_context = _official_context(notice_id, plan.get("option_id"))
    llm_response = _coach_chat_with_llm(notice, plan, profile, message, official_context=official_context, page_context=page_context)
    if llm_response:
        return llm_response

    normalized = message.replace(" ", "").lower()
    if any(keyword in normalized for keyword in ["사용법", "이용", "어떻게", "화면", "페이지", "버튼", "어디", "메뉴", "설명"]):
        reply = _service_usage_reply(page_context)
        actions = _service_usage_actions(page_context)
    elif any(keyword in normalized for keyword in ["부족", "계약금", "돈", "자금", "얼마"]):
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
        "page_context": _safe_page_context(page_context),
        "reply": sanitize_reply(reply),
        "suggested_actions": sanitize_actions(actions),
        "context_refs": official_context["refs"],
    }
    _save_chat_log(response, message, provider="template", safety_flags=safety_flags(reply))
    return response


def _coach_chat_with_llm(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    message: str,
    *,
    official_context: dict[str, Any],
    page_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not llm_enabled("chat"):
        return None

    page_context = page_context or {}
    context = _chat_context(notice, plan, profile, official_context=official_context, page_context=page_context)
    started_at = perf_counter()
    try:
        ai_response = chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 FirstHome Navigator AI의 청약 준비 코치입니다. "
                        "동시에 서비스 전역 챗봇입니다. 사용자가 현재 보고 있는 화면의 목적, 버튼, 다음 이동 경로, 서비스 이용 방법도 설명합니다. "
                        "답변은 한국어 2~4문장, 420자 이내로 작성합니다. "
                        "질문이 서비스 이용법이면 현재 화면명과 다음 행동을 먼저 말하고, 질문이 청약/자금이면 선택 공고와 옵션 기준으로 답합니다. "
                        "금액과 날짜가 있으면 먼저 말하고, 불확실한 일반론이나 보장 표현은 피합니다. "
                        "당첨, 신청 가능, 자격 충족, 대출 승인 같은 확정 표현은 금지합니다. "
                        "청약 조건, 금액, 일정에 답할 때는 공식 공고문 확인이 필요하다는 취지를 포함합니다. "
                        "단순 화면 사용법 질문에는 공식 공고문 문구를 억지로 반복하지 말고, 필요하면 '실제 신청 판단은 공식 공고문이 우선' 정도로 짧게 덧붙입니다."
                    ),
                },
                {"role": "user", "content": f"컨텍스트:\n{context}\n\n질문:\n{message}"},
            ],
            response_schema=COACH_CHAT_SCHEMA,
            temperature=0.2,
        )
        latency_ms = round((perf_counter() - started_at) * 1000)
    except AiClientError as exc:
        latency_ms = round((perf_counter() - started_at) * 1000)
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
            latency_ms=latency_ms,
        )
        return None

    payload = ai_response.parsed_json or {}
    response = {
        "source": "llm",
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "option_id": plan.get("option_id"),
        "page_context": _safe_page_context(page_context),
        "reply": sanitize_reply(str(payload.get("reply", ""))),
        "suggested_actions": sanitize_actions([str(action) for action in payload.get("suggested_actions", [])]),
        "context_refs": payload.get("context_refs") or official_context["refs"],
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
        latency_ms=latency_ms,
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


def _service_usage_reply(page_context: dict[str, Any]) -> str:
    page_type = str(page_context.get("page_type") or "")
    page_labels = {
        "home": "대시보드",
        "profile": "조건 입력",
        "recommendations": "추천 청약",
        "notice_detail": "청약 세부",
        "funding": "자금 로드맵",
        "ai_coach": "AI 코치",
        "map": "청약 지도",
        "favorites": "관심목록",
    }
    label = page_labels.get(page_type, "현재 화면")
    if page_type == "profile":
        return "조건 입력 화면에서는 소득, 보유 현금, 희망 지역, 공급 유형을 저장합니다. 저장 후 추천 청약으로 이동하면 이 조건을 기준으로 후보와 주택형 옵션 점수가 다시 계산됩니다."
    if page_type == "recommendations":
        return "추천 청약 화면은 조건에 맞는 공고와 대표 주택형 옵션을 점수순으로 보여줍니다. 공고를 열어 세부 조건을 확인하고, 원하는 옵션의 자금 보기를 눌러 계약금과 납부 흐름을 비교하세요."
    if page_type == "notice_detail":
        return "청약 세부 화면에서는 공식 확인 체크리스트, 주요 일정, 주택형 옵션을 확인합니다. 옵션을 바꾸면 자금 로드맵과 AI 코치도 그 선택 기준으로 이어집니다."
    if page_type == "funding":
        return "자금 로드맵 화면은 선택한 주택형 기준으로 분양가, 계약금, 부족액, 중도금·잔금·융자금 흐름을 정리합니다. 상단의 AI 코칭 받기로 넘어가면 다음 행동을 더 구체적으로 볼 수 있습니다."
    if page_type == "ai_coach":
        return "AI 코치 화면은 이미 선택한 청약과 주택형을 기준으로 이번 주 해야 할 일, 확인할 조건, 자금 준비 방향을 정리합니다. 빠른 질문은 오른쪽 챗봇에서 하고, 깊은 실행 계획은 이 화면을 기준으로 보면 됩니다."
    if page_type == "map":
        return "청약 지도 화면은 지역별 공고를 빠르게 훑어보는 곳입니다. 관심 지역의 공고를 선택한 뒤 옵션 보기로 들어가면 세부 조건과 자금 로드맵으로 이어집니다."
    if page_type == "favorites":
        return "관심목록 화면은 저장한 공고, 주택형 옵션, 금융상품, 정책을 모아 보는 곳입니다. 저장한 옵션은 바로 자금 로드맵으로 이동해 다시 비교할 수 있습니다."
    return f"{label}에서 궁금한 버튼이나 청약 조건을 물어보면, 현재 선택된 공고와 옵션 또는 입력 조건을 기준으로 설명해드립니다."


def _service_usage_actions(page_context: dict[str, Any]) -> list[str]:
    page_type = str(page_context.get("page_type") or "")
    actions_by_page = {
        "home": ["조건 입력에서 프로필을 저장하세요.", "추천 청약에서 후보를 선택하세요.", "선택 후 자금 로드맵을 확인하세요."],
        "profile": ["조건을 저장하고 추천 청약으로 이동하세요.", "희망 지역과 공급 유형을 먼저 선택하세요.", "보유 현금과 월 저축 가능액을 현실적으로 입력하세요."],
        "recommendations": ["상위 후보의 대표 옵션을 확인하세요.", "공고 상세에서 체크리스트를 보세요.", "옵션 자금 보기로 부족액을 비교하세요."],
        "notice_detail": ["주택형 옵션을 하나 선택하세요.", "공식 확인 체크리스트를 확인하세요.", "옵션 자금 보기로 이동하세요."],
        "funding": ["계약금 부족액과 월 목표를 확인하세요.", "다른 옵션과 간단히 비교하세요.", "AI 코칭 받기로 다음 행동을 정리하세요."],
        "ai_coach": ["바로 처리할 일을 확인하세요.", "공식 원문 또는 fixture 안내를 구분하세요.", "필요하면 추천 목록에서 다른 후보를 선택하세요."],
        "map": ["지역 공고를 선택하세요.", "옵션 보기로 세부 화면에 들어가세요.", "관심 공고는 저장해두세요."],
        "favorites": ["저장 옵션의 자금 보기를 열어보세요.", "관심 공고를 다시 비교하세요.", "필요 없는 항목은 정리하세요."],
    }
    return actions_by_page.get(page_type, ["현재 화면의 버튼 이름을 질문해보세요.", "청약 조건이나 자금 흐름을 물어보세요.", "선택한 공고가 있으면 세부 답변이 더 정확해집니다."])


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


def _coach_summary_context(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    official_context: dict[str, Any],
) -> str:
    option_label = f"{plan.get('unit_type', '공고 대표값')} {plan.get('floor_group', '')}".strip()
    shortfall = int(plan.get("shortfall") or 0)
    monthly_target = int(plan.get("monthly_target") or 0)
    deadline = str(notice.get("application_deadline") or "공식 확인 필요")
    required_documents = _unique_strings(
        [
            *(notice.get("required_documents") or []),
            *official_context.get("required_document_lines", []),
        ],
        limit=20,
    )
    required_document_line = ", ".join(required_documents[:18]) or "공식 공고문에서 제출서류 확인 필요"
    option_extra_price = int(plan.get("balcony_extension_price") or 0)
    option_extra_line = (
        f"구조화된 추가 선택품목 금액 {option_extra_price:,}원"
        if option_extra_price > 0
        else "구조화된 추가 선택품목 금액 없음. 0원은 무료 확정이 아니라 선택품목/감액/별도계약 여부를 공식 원문에서 확인해야 함"
    )
    deep_review_lines = "\n".join(official_context.get("deep_review_lines", [])[:18])
    personalization_brief = (
        f"개인화 핵심: 사용자는 {notice['title']}의 {option_label} 옵션을 보고 있습니다. "
        f"계약금은 {int(plan.get('down_payment') or 0):,}원, 보유 현금은 {int(profile.get('asset') or 0):,}원, "
        f"계약금 부족액은 {shortfall:,}원, 월 준비 목표는 {monthly_target:,}원, 접수 마감은 {deadline}입니다. "
        f"추가 선택품목/감액 정보는 {option_extra_line}이며, 제출서류 후보는 {required_document_line}입니다. "
        "할 일과 선택 판단은 이 값들을 직접 반영해야 합니다."
    )
    top_options = "\n".join(
        (
            f"- {option.get('unit_type')} {option.get('floor_group')}: "
            f"분양가 {int(option.get('base_price') or 0):,}원, "
            f"계약금 {int(option.get('down_payment') or 0):,}원, "
            f"점수 {int(option.get('option_fit_score') or 0)}점"
        )
        for option in recommendation.get("top_options", [])[:5]
    )
    timeline = "\n".join(
        f"- {row.get('label')}: {row.get('date')} / {int(row.get('amount') or 0):,}원"
        for row in plan.get("timeline", [])[:8]
    )
    checklists = "\n".join(official_context["checklist_lines"][:6]) or "- 공식 체크리스트는 아직 연결되지 않았습니다."
    evidence = "\n".join(official_context["evidence_lines"][:6]) or "- 공식 근거 문장은 아직 연결되지 않았습니다."
    source_note = (
        "자료 성격: Fixture 보강 데이터입니다. 실제 공식 PDF 원문과 공식 출처 URL이 없으므로 페이지 기반 공식 원문 확인은 제공되지 않습니다. "
        "아래 체크리스트와 근거 후보는 fixture 구조화 데이터와 LLM 해석을 위한 참고 컨텍스트입니다."
        if official_context.get("is_fixture")
        else "자료 성격: 실제 공고문 또는 공고문 분석 결과 기반입니다. 최종 신청 전 공식 원문 확인이 필요합니다."
    )
    return (
        f"{source_note}\n"
        f"{personalization_brief}\n"
        f"공고: {notice['title']}\n"
        f"지역/공급유형: {notice['region']} {notice['district']} / {notice['supply_type']}\n"
        f"추천 점수: {recommendation.get('total_score')}/{recommendation.get('score_max', 100)}\n"
        f"점수 상세: {recommendation.get('score_detail')}\n"
        f"선택 옵션: {plan.get('unit_type', '공고 대표값')} {plan.get('floor_group', '')}\n"
        f"옵션 유형: {plan.get('option_type', '')}\n"
        f"분양가: {plan.get('price', 0):,}원\n"
        f"계약금: {plan.get('down_payment', 0):,}원\n"
        f"중도금: {plan.get('middle_payment', 0):,}원\n"
        f"잔금: {plan.get('final_payment', 0):,}원\n"
        f"융자금: {plan.get('loan_amount', 0):,}원\n"
        f"추가 선택품목/감액/별도계약 정보: {option_extra_line}\n"
        f"사용자 보유 현금: {int(profile.get('asset') or 0):,}원\n"
        f"월 저축 가능액: {int(profile.get('monthly_saving') or 0):,}원\n"
        f"계약금 부족액: {plan.get('shortfall', 0):,}원\n"
        f"월 준비 목표: {plan.get('monthly_target', 0):,}원\n"
        f"접수 마감: {notice.get('application_deadline')}\n"
        f"당첨자 발표: {notice.get('winner_date')}\n"
        f"계약일: {notice.get('contract_date')}\n"
        f"제출서류 후보: {required_document_line}\n"
        f"Top 주택형 옵션:\n{top_options or '- 옵션 비교 데이터 없음'}\n"
        f"납부 일정:\n{timeline or '- 납부 일정 확인 필요'}\n"
        f"공식 확인 체크리스트:\n{checklists}\n"
        f"공고문 심층 검토 근거 후보:\n{deep_review_lines or '- 심층 검토 근거 후보 없음. 원문 확인 필요'}\n"
        f"공식 근거 후보:\n{evidence}"
    )


def _chat_context(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    *,
    official_context: dict[str, Any],
    page_context: dict[str, Any] | None = None,
) -> str:
    page_context = page_context or {}
    timeline = "\n".join(
        f"- {row.get('label')}: {row.get('date')} / {int(row.get('amount') or 0):,}원"
        for row in plan.get("timeline", [])[:8]
    )
    evidence = "\n".join(official_context["evidence_lines"][:6]) or "- 공식 근거 문장은 아직 연결되지 않았습니다."
    checklists = "\n".join(official_context["checklist_lines"][:5]) or "- 공식 체크리스트는 아직 연결되지 않았습니다."
    analysis = "\n".join(official_context["analysis_lines"][:5]) or "- 공식 분석 상태 정보가 아직 연결되지 않았습니다."
    page = _page_context_text(page_context)
    return (
        f"현재 화면 컨텍스트:\n{page}\n"
        f"공고: {notice['title']}\n"
        f"지역/공급유형: {notice['region']} {notice['district']} / {notice['supply_type']}\n"
        f"선택 옵션: {plan.get('unit_type', '공고 대표값')} {plan.get('floor_group', '')}\n"
        f"옵션 유형: {plan.get('option_type', '')}\n"
        f"분양가: {plan.get('price', 0):,}원\n"
        f"계약금: {plan.get('down_payment', 0):,}원\n"
        f"중도금: {plan.get('middle_payment', 0):,}원\n"
        f"잔금: {plan.get('final_payment', 0):,}원\n"
        f"융자금: {plan.get('loan_amount', 0):,}원\n"
        f"부족액: {plan.get('shortfall', 0):,}원\n"
        f"월 준비 목표: {plan.get('monthly_target', 0):,}원\n"
        f"사용자 자산: {int(profile.get('asset') or 0):,}원\n"
        f"월 저축 가능액: {int(profile.get('monthly_saving') or 0):,}원\n"
        f"분석 상태:\n{analysis}\n"
        f"타임라인:\n{timeline}\n"
        f"공식 근거 후보:\n{evidence}\n"
        f"공식 확인 체크리스트:\n{checklists}"
    )


def _page_context_text(page_context: dict[str, Any]) -> str:
    if not page_context:
        return "- 화면 정보 없음"
    safe = _safe_page_context(page_context)
    labels = {
        "home": "대시보드",
        "profile": "조건 입력",
        "recommendations": "추천 청약",
        "notice_detail": "청약 세부",
        "funding": "자금 로드맵",
        "ai_coach": "AI 코치",
        "map": "청약 지도",
        "favorites": "관심목록",
        "auth": "계정",
    }
    page_type = safe.get("page_type") or "unknown"
    lines = [
        f"- 화면: {labels.get(page_type, page_type)}",
        f"- 경로: {safe.get('path') or ''}",
        f"- 로그인 여부: {'로그인' if safe.get('is_authenticated') else '비로그인'}",
        f"- 선택 공고 ID: {safe.get('notice_id') or '없음'}",
        f"- 선택 옵션 ID: {safe.get('option_id') or '없음'}",
    ]
    if safe.get("notice_title"):
        lines.append(f"- 선택 공고명: {safe['notice_title']}")
    if safe.get("option_label"):
        lines.append(f"- 선택 옵션: {safe['option_label']}")
    return "\n".join(lines)


def _safe_page_context(page_context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(page_context, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in ["path", "page_type", "notice_title", "option_label"]:
        value = str(page_context.get(key) or "").strip()
        if value:
            safe[key] = value[:160]
    for key in ["notice_id", "option_id"]:
        try:
            value = int(page_context.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            safe[key] = value
    safe["is_authenticated"] = bool(page_context.get("is_authenticated"))
    return safe


def _official_context(notice_id: int, option_id: int | None) -> dict[str, Any]:
    refs: list[dict[str, str]] = [
        {"type": "notice", "id": str(notice_id), "label": "공고 기본 정보"},
        {"type": "funding_plan", "id": f"notice:{notice_id}:option:{option_id or 'representative'}", "label": "자금 로드맵"},
    ]
    is_fixture = False
    evidence_lines: list[str] = []
    checklist_lines: list[str] = []
    analysis_lines: list[str] = []
    required_document_lines: list[str] = []
    additional_option_lines: list[str] = []
    deep_review_lines: list[str] = []
    try:
        from apps.notice_docs.models import EligibilityChecklist, ExtractionEvidence, HousingUnitOption, NoticeExtraction
        from apps.notice_docs.services.status import notice_analysis_summary
        from apps.notices.models import HousingNotice

        notice_obj = HousingNotice.objects.filter(id=notice_id).first()
        if notice_obj is not None:
            source_meta = notice_obj.source_meta if isinstance(notice_obj.source_meta, dict) else {}
            is_fixture = bool(source_meta.get("fixture_id")) or str(notice_obj.source_id or "").startswith("fixture-")
            summary = notice_analysis_summary(notice_obj)
            analysis_lines.append(f"- 공식 분석: {summary.get('label')} / 단계 {summary.get('stage')}")
            if is_fixture:
                refs.append({"type": "fixture", "id": str(source_meta.get("fixture_id") or notice_id), "label": "Fixture 보강 데이터"})
                analysis_lines.append("- Fixture 안내: 실제 공식 PDF 원문과 공식 출처 URL이 없는 발표용 보강 데이터")
                evidence_lines.append("- Fixture 데이터: 실제 PDF 원문이 없어 페이지 기반 공식 근거는 제공되지 않음")
                checklist_lines.append("- Fixture 안내: 공식 원문 확인 항목은 실제 PDF가 없어 확인 불가")
                deep_review_lines.append("- Fixture 안내: 구조화된 fixture 값과 LLM 해석 기준으로만 검토 가능")
            for issue in summary.get("review_issues", [])[:3]:
                analysis_lines.append(f"- 검토 이슈: {issue.get('title')} - {issue.get('message')}")
            required_document_lines.extend(_unique_strings(notice_obj.required_documents or [], limit=20))

        option = None
        if option_id:
            option = (
                HousingUnitOption.objects.filter(id=option_id, notice_id=notice_id)
                .prefetch_related("payment_schedules")
                .first()
            )
        if option is None:
            option = (
                HousingUnitOption.objects.filter(notice_id=notice_id)
                .prefetch_related("payment_schedules")
                .order_by("-confidence", "exclusive_area_m2", "id")
                .first()
            )
        if option is not None:
            refs.append({"type": "unit_option", "id": str(option.id), "label": f"{option.unit_type} {option.floor_group}".strip()})
            analysis_lines.append(
                f"- 선택 옵션 신뢰도: {round(float(option.confidence or 0) * 100)}%, 융자금 {int(option.loan_amount or 0):,}원"
            )
            if option.source_text:
                evidence_lines.append(_source_line("주택형/분양가", option.source_page, option.source_text))
                if _looks_like_additional_option_text(option.source_text):
                    additional_option_lines.append(_source_line("선택 옵션/주택형 근거", option.source_page, option.source_text))
                if _looks_like_deep_review_text(option.source_text):
                    deep_review_lines.append(_source_line("주택형/공고문 세부조건", option.source_page, option.source_text))
            for schedule in option.payment_schedules.all()[:6]:
                refs.append({"type": "payment_schedule", "id": str(schedule.id), "label": schedule.label})
                if schedule.evidence_text:
                    evidence_lines.append(_source_line(schedule.label, option.source_page, schedule.evidence_text))
                    if _looks_like_additional_option_text(schedule.evidence_text):
                        additional_option_lines.append(_source_line(schedule.label, option.source_page, schedule.evidence_text))
                    if _looks_like_deep_review_text(schedule.evidence_text):
                        deep_review_lines.append(_source_line(schedule.label, option.source_page, schedule.evidence_text))

        for item in EligibilityChecklist.objects.filter(notice_id=notice_id).order_by("category", "id")[:16]:
            refs.append({"type": "checklist", "id": str(item.id), "label": item.title})
            page = f"{item.page_no}쪽" if item.page_no else "페이지 확인 필요"
            checklist_lines.append(f"- {item.title}: {page}, 신뢰도 {round(float(item.confidence or 0) * 100)}%")
            if item.evidence_text:
                evidence_lines.append(_source_line(item.title, None, item.evidence_text))
                if _looks_like_additional_option_text(item.evidence_text):
                    additional_option_lines.append(_source_line(item.title, item.page_no, item.evidence_text))
                if _looks_like_deep_review_text(item.title) or _looks_like_deep_review_text(item.evidence_text):
                    deep_review_lines.append(_source_line(item.title, item.page_no, item.evidence_text or item.condition_text))

        latest_extraction = NoticeExtraction.objects.filter(notice_id=notice_id).order_by("-created_at", "-id").first()
        raw_json = latest_extraction.raw_json if latest_extraction and isinstance(latest_extraction.raw_json, dict) else {}
        for document in raw_json.get("required_documents", [])[:20] if isinstance(raw_json, dict) else []:
            refs.append({"type": "required_document", "id": str(document), "label": str(document)})
            checklist_lines.append(f"- 필수서류: {document}")
            required_document_lines.append(str(document))

        for text in _walk_text_values(raw_json):
            if _looks_like_additional_option_text(text):
                additional_option_lines.append(_source_line("발코니/추가 선택품목 후보", None, text))
            if _looks_like_deep_review_text(text):
                deep_review_lines.append(_source_line("공고문 세부조건 후보", None, text))

        for evidence in ExtractionEvidence.objects.filter(extraction__notice_id=notice_id).order_by("id")[:32]:
            refs.append({"type": "evidence", "id": str(evidence.id), "label": evidence.field_path})
            evidence_lines.append(_source_line(evidence.field_path, evidence.page_no, evidence.source_text))
            if _looks_like_additional_option_text(evidence.source_text) or _looks_like_additional_option_text(evidence.field_path):
                additional_option_lines.append(_source_line(evidence.field_path, evidence.page_no, evidence.source_text))
            if _looks_like_deep_review_text(evidence.source_text) or _looks_like_deep_review_text(evidence.field_path):
                deep_review_lines.append(_source_line(evidence.field_path, evidence.page_no, evidence.source_text))
    except Exception:
        return {
            "refs": refs,
            "is_fixture": is_fixture,
            "evidence_lines": evidence_lines,
            "checklist_lines": checklist_lines,
            "analysis_lines": analysis_lines,
            "required_document_lines": _unique_strings(required_document_lines, limit=20),
            "additional_option_lines": _unique_strings(additional_option_lines, limit=10),
            "deep_review_lines": _unique_strings([*deep_review_lines, *additional_option_lines], limit=20),
        }
    return {
        "refs": refs,
        "is_fixture": is_fixture,
        "evidence_lines": _unique_strings(evidence_lines, limit=24),
        "checklist_lines": _unique_strings(checklist_lines, limit=16),
        "analysis_lines": _unique_strings(analysis_lines, limit=12),
        "required_document_lines": _unique_strings(required_document_lines, limit=20),
        "additional_option_lines": _unique_strings(additional_option_lines, limit=10),
        "deep_review_lines": _unique_strings([*deep_review_lines, *additional_option_lines, *checklist_lines], limit=24),
    }


def _source_line(label: str, page_no: int | None, text: str) -> str:
    page = f"{page_no}쪽" if page_no else "페이지 확인 필요"
    snippet = " ".join(str(text or "").split())[:220]
    return f"- {label} ({page}): {snippet}"


def _is_authenticated_user(user: Any) -> bool:
    return bool(user and not isinstance(user, AnonymousUser) and getattr(user, "is_authenticated", False))


def _is_fixture_notice(notice: dict[str, Any] | None) -> bool:
    if not notice:
        return False
    source_meta = notice.get("source_meta") if isinstance(notice.get("source_meta"), dict) else {}
    data_source = str(notice.get("data_source") or "").casefold()
    source_id = str(notice.get("source_id") or "").casefold()
    return "fixture" in data_source or source_id.startswith("fixture-") or bool(source_meta.get("fixture_id"))


def _coach_plan_input_hash(
    notice: dict[str, Any],
    plan: dict[str, Any],
    profile: dict[str, Any],
    official_context: dict[str, Any],
) -> str:
    relevant_profile_keys = [
        "name",
        "birth_year",
        "income",
        "asset",
        "debt",
        "monthly_saving",
        "preferred_regions",
        "preferred_area_min",
        "preferred_area_max",
        "preferred_price_min",
        "preferred_price_max",
        "special_conditions",
        "supply_types",
        "housing_status",
        "subscription_months",
    ]
    official_fingerprint = {
        "refs": official_context.get("refs", [])[:24],
        "required_documents": official_context.get("required_document_lines", [])[:20],
        "additional_options": official_context.get("additional_option_lines", [])[:10],
        "deep_review": official_context.get("deep_review_lines", [])[:24],
        "evidence": official_context.get("evidence_lines", [])[:12],
    }
    payload = {
        "notice_id": notice.get("id"),
        "notice_updated_at": str(notice.get("updated_at", "")),
        "option_id": int(plan.get("option_id") or 0),
        "price": int(plan.get("price") or 0),
        "down_payment": int(plan.get("down_payment") or 0),
        "shortfall": int(plan.get("shortfall") or 0),
        "monthly_target": int(plan.get("monthly_target") or 0),
        "timeline": plan.get("timeline", []),
        "profile": {key: profile.get(key) for key in relevant_profile_keys if key in profile},
        "official": official_fingerprint,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _looks_like_additional_option_text(text: Any) -> bool:
    normalized = str(text or "").replace(" ", "")
    if not normalized:
        return False
    keywords = [
        "발코니",
        "확장",
        "추가선택",
        "추가선택품목",
        "선택품목",
        "유상옵션",
        "무상옵션",
        "플러스옵션",
        "별도계약",
    ]
    return any(keyword in normalized for keyword in keywords)


def _looks_like_deep_review_text(text: Any) -> bool:
    normalized = str(text or "").replace(" ", "")
    if not normalized:
        return False
    keywords = [
        "지역우선",
        "우선공급",
        "거주기간",
        "화성시",
        "경기도",
        "전입",
        "다자녀",
        "신혼부부",
        "생애최초",
        "노부모",
        "기관추천",
        "특별공급",
        "일반공급",
        "소득",
        "자산",
        "청약통장",
        "입주자저축",
        "무주택",
        "세대구성",
        "전매",
        "거주의무",
        "재당첨",
        "부적격",
        "서류",
        "제출",
        "증명서",
        "선택품목",
        "추가선택",
        "유상옵션",
        "무상옵션",
        "감액",
        "할인",
        "별도계약",
        "납부",
        "중도금",
        "잔금",
        "융자",
    ]
    return any(keyword in normalized for keyword in keywords)


def _walk_text_values(value: Any, *, limit: int = 80) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, str):
            text = " ".join(node.split())
            if text:
                found.append(text)
            return
        if isinstance(node, dict):
            for key, child in node.items():
                if len(found) >= limit:
                    break
                if _looks_like_additional_option_text(key):
                    found.append(str(key))
                walk(child)
            return
        if isinstance(node, list):
            for child in node:
                if len(found) >= limit:
                    break
                walk(child)

    walk(value)
    return found


def _unique_strings(items: list[Any], *, limit: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = " ".join(str(item or "").split())
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
        if len(cleaned) >= limit:
            break
    return cleaned


def _sanitize_decision_points(points: Any) -> list[dict[str, str]]:
    if not isinstance(points, list):
        return []
    cleaned: list[dict[str, str]] = []
    for point in points[:3]:
        if not isinstance(point, dict):
            continue
        title = sanitize_actions([str(point.get("title", ""))], limit=1)
        body = sanitize_actions([str(point.get("body", ""))], limit=1)
        cta = sanitize_actions([str(point.get("cta", ""))], limit=1)
        if title and body:
            cleaned.append(
                {
                    "title": title[0],
                    "body": body[0],
                    "cta": cta[0] if cta else "자세히 보기",
                }
            )
    return cleaned


def _sanitize_deep_review_items(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in items[:6]:
        if not isinstance(item, dict):
            continue
        title = sanitize_actions([str(item.get("title", ""))], limit=1)
        body = sanitize_actions([str(item.get("body", ""))], limit=1)
        why = sanitize_actions([str(item.get("why_it_matters", ""))], limit=1)
        if title and body:
            cleaned.append(
                {
                    "title": title[0],
                    "body": body[0],
                    "why_it_matters": why[0] if why else "해당 조건은 신청 가능성이나 실제 부담금에 영향을 줄 수 있습니다.",
                }
            )
    return cleaned


def _save_chat_log(
    response: dict[str, Any],
    question: str,
    *,
    provider: str,
    model_name: str = "",
    raw_response: dict[str, Any] | None = None,
    error_message: str = "",
    safety_flags: list[str] | None = None,
    latency_ms: int = 0,
) -> None:
    answer = str(response.get("reply") or response.get("summary") or "")
    AiChatLog.objects.create(
        notice_id=response.get("notice_id"),
        option_id=response.get("option_id"),
        question=question,
        answer=answer,
        provider=provider,
        model_name=model_name,
        source_refs=response.get("context_refs", []),
        safety_flags=safety_flags or [],
        raw_response=raw_response or {},
        error_message=error_message,
        latency_ms=max(0, latency_ms),
        prompt_chars=len(question),
        response_chars=len(answer),
        estimated_cost_krw=_estimated_cost_krw(raw_response or {}),
    )


def _estimated_cost_krw(raw_response: dict[str, Any]) -> int:
    usage = raw_response.get("usage") if isinstance(raw_response, dict) else None
    if not isinstance(usage, dict):
        return 0
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    if prompt_tokens <= 0 and completion_tokens <= 0:
        return 0
    return round((prompt_tokens * 0.0002 + completion_tokens * 0.0006) * 1400 / 1000)
