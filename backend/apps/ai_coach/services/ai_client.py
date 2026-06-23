from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings


class AiClientError(RuntimeError):
    pass


class AiProviderUnavailable(AiClientError):
    pass


@dataclass(frozen=True)
class AiClientResponse:
    provider: str
    model: str
    content: str
    parsed_json: dict[str, Any] | None
    raw_response: dict[str, Any]


def configured_provider() -> str:
    return str(settings.AI_SETTINGS.get("PROVIDER", "template")).lower()


def llm_enabled(feature: str) -> bool:
    if configured_provider() == "template":
        return False
    flag_name = "ENABLE_LLM_CHAT" if feature == "chat" else "ENABLE_LLM_EXTRACTION"
    return bool(settings.AI_SETTINGS.get(flag_name, False))


def chat_completion(
    *,
    messages: list[dict[str, str]],
    response_schema: dict[str, Any] | None = None,
    temperature: float = 0.2,
) -> AiClientResponse:
    provider = configured_provider()
    if provider == "template":
        raise AiProviderUnavailable("AI_PROVIDER=template")

    endpoint = _endpoint_for_provider(provider)
    api_key = _api_key_for_provider(provider)
    model = str(settings.AI_SETTINGS.get("MODEL", "gpt-4.1"))
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": response_schema,
        }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=int(settings.AI_SETTINGS.get("REQUEST_TIMEOUT", 30)),
        )
        response.raise_for_status()
        raw = response.json()
    except requests.RequestException as exc:
        raise AiClientError(str(exc)) from exc
    except ValueError as exc:
        raise AiClientError("LLM response was not valid JSON.") from exc

    content = _content_from_chat_response(raw)
    return AiClientResponse(
        provider=provider,
        model=model,
        content=content,
        parsed_json=_parse_json_content(content),
        raw_response=raw,
    )


def _endpoint_for_provider(provider: str) -> str:
    if provider == "openai":
        base_url = str(settings.AI_SETTINGS.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/") + "/"
        path = str(settings.AI_SETTINGS.get("OPENAI_CHAT_PATH", "/chat/completions")).lstrip("/")
        return urljoin(base_url, path)
    if provider in {"gms", "gms_openai"}:
        base_url = str(
            settings.AI_SETTINGS.get("GMS_OPENAI_BASE_URL", "https://gms.ssafy.io/gmsapi/api.openai.com/v1")
        ).rstrip("/") + "/"
        path = str(settings.AI_SETTINGS.get("GMS_OPENAI_CHAT_PATH", "/chat/completions")).lstrip("/")
        return urljoin(base_url, path)
    raise AiProviderUnavailable(f"Unsupported AI_PROVIDER={provider}")


def _api_key_for_provider(provider: str) -> str:
    if provider == "openai":
        api_key = str(settings.AI_SETTINGS.get("OPENAI_API_KEY", ""))
        if not api_key:
            raise AiProviderUnavailable("OPENAI_API_KEY is missing.")
        return api_key
    if provider in {"gms", "gms_openai"}:
        api_key = str(settings.AI_SETTINGS.get("GMS_API_KEY", "") or settings.AI_SETTINGS.get("OPENAI_API_KEY", ""))
        if not api_key:
            raise AiProviderUnavailable("GMS_API_KEY is missing.")
        return api_key
    return ""


def _content_from_chat_response(raw: dict[str, Any]) -> str:
    try:
        return str(raw["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError) as exc:
        raise AiClientError("Unexpected chat completion response shape.") from exc


def _parse_json_content(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
