from __future__ import annotations

import copy
import hashlib
import re
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.api_schema import TAGS, VIDEOS_RESPONSE


DEFAULT_QUERY = "청약 공공분양 주택청약 내집마련"
YOUTUBE_SEARCH_CACHE_SECONDS = 60 * 60 * 6
YOUTUBE_STALE_CACHE_SECONDS = 60 * 60 * 24 * 7
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 50

DEFAULT_VIDEO_ITEMS = [
    {
        "video_id": "8v-LHYV3zZM",
        "title": "2026년 공공분양 입주자모집 계획",
        "channel_title": "거북이 지도",
        "published_at": "",
        "thumbnail_url": "https://img.youtube.com/vi/8v-LHYV3zZM/mqdefault.jpg",
        "description": "2026년 공공분양 입주자모집 계획을 빠르게 확인하는 기본 추천 영상입니다.",
        "embed_url": "https://www.youtube.com/embed/8v-LHYV3zZM",
        "watch_url": "https://www.youtube.com/watch?v=8v-LHYV3zZM",
    },
    {
        "video_id": "-fYhyIXTjj8",
        "title": "공공분양 vs 민간분양 차이점 완벽정리",
        "channel_title": "청알남_청약알려주는남자",
        "published_at": "",
        "thumbnail_url": "https://img.youtube.com/vi/-fYhyIXTjj8/mqdefault.jpg",
        "description": "공공분양과 민간분양의 차이를 비교하는 기본 추천 영상입니다.",
        "embed_url": "https://www.youtube.com/embed/-fYhyIXTjj8",
        "watch_url": "https://www.youtube.com/watch?v=-fYhyIXTjj8",
    },
    {
        "video_id": "Mmdhq70nDcY",
        "title": "공공분양 본격시작! 청약 준비 내집마련",
        "channel_title": "한문도TV_부동산채널",
        "published_at": "",
        "thumbnail_url": "https://img.youtube.com/vi/Mmdhq70nDcY/mqdefault.jpg",
        "description": "공공분양 공급 흐름을 살펴보는 기본 추천 영상입니다.",
        "embed_url": "https://www.youtube.com/embed/Mmdhq70nDcY",
        "watch_url": "https://www.youtube.com/watch?v=Mmdhq70nDcY",
    },
]


@extend_schema(
    tags=[TAGS["videos"]],
    summary="기본 청약 영상 목록",
    description="시연 진입 시 YouTube API 쿼터를 쓰지 않도록 고정 추천 영상 3개를 반환합니다.",
    responses={200: VIDEOS_RESPONSE},
)
@api_view(["GET"])
def default_videos_view(_request):
    return Response(
        {
            "items": DEFAULT_VIDEO_ITEMS,
            "fallback": False,
            "cache": True,
            "cache_type": "static_default",
            "query": DEFAULT_QUERY,
        }
    )


@extend_schema(
    tags=[TAGS["videos"]],
    summary="청약 영상 검색",
    description="검색어 기준 YouTube 청약 관련 영상을 최대 3개 반환합니다. 동일 검색어는 캐시를 우선 사용합니다.",
    parameters=[OpenApiParameter("q", str, OpenApiParameter.QUERY, description="영상 검색어")],
    responses={200: VIDEOS_RESPONSE},
)
@api_view(["GET"])
def search_videos_view(request):
    query = _normalize_query(request.query_params.get("q", "")) or "청약"
    return _youtube_response(query)


def _youtube_response(query: str):
    normalized_query = _normalize_query(query) or DEFAULT_QUERY
    cache_key = _make_youtube_cache_key(normalized_query)
    stale_cache_key = _make_youtube_stale_cache_key(normalized_query)

    cached_payload = _cache_payload(cache_key, cache_type="fresh")
    if cached_payload:
        return Response(cached_payload)

    api_key = settings.EXTERNAL_API_KEYS.get("YOUTUBE_API_KEY", "")
    if not api_key:
        stale_payload = _cache_payload(
            stale_cache_key,
            cache_type="stale",
            fallback_reason="YouTube API 키가 없어 이전 검색 성공 결과를 표시합니다.",
        )
        if stale_payload:
            return Response(stale_payload)
        return Response(
            {
                "items": [],
                "fallback": True,
                "cache": False,
                "query": normalized_query,
                "fallback_reason": "YouTube API 키가 없어 영상을 불러오지 못했습니다. backend/.env의 YOUTUBE_API_KEY를 확인해 주세요.",
            }
        )

    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": normalized_query,
                "type": "video",
                "maxResults": 3,
                "key": api_key,
                "safeSearch": "moderate",
                "relevanceLanguage": "ko",
                "regionCode": "KR",
                "order": "relevance",
            },
            timeout=10,
        )
        response.raise_for_status()
        items = [
            _serialize_video(item)
            for item in response.json().get("items", [])
            if item.get("id", {}).get("videoId")
        ]
    except requests.RequestException as exc:
        stale_payload = _cache_payload(
            stale_cache_key,
            cache_type="stale",
            fallback_reason="YouTube API 호출 실패로 이전 검색 성공 결과를 표시합니다.",
        )
        if stale_payload:
            return Response(stale_payload)
        status_code = exc.response.status_code if exc.response else "network"
        return Response(
            {
                "items": [],
                "fallback": True,
                "cache": False,
                "query": normalized_query,
                "fallback_reason": f"YouTube API 응답을 받지 못했습니다. 키, 할당량, 호출 허용 설정을 확인해 주세요. ({status_code})",
            }
        )

    if not items:
        stale_payload = _cache_payload(
            stale_cache_key,
            cache_type="stale",
            fallback_reason="새 검색 결과가 없어 이전 검색 성공 결과를 표시합니다.",
        )
        if stale_payload:
            return Response(stale_payload)
        return Response(
            {
                "items": [],
                "fallback": True,
                "cache": False,
                "query": normalized_query,
                "fallback_reason": "청약 관련 영상 검색 결과가 없습니다. 검색어를 바꿔 다시 시도해 주세요.",
            }
        )

    payload = {
        "items": items,
        "fallback": False,
        "cache": False,
        "query": normalized_query,
    }
    cache.set(cache_key, copy.deepcopy(payload), YOUTUBE_SEARCH_CACHE_SECONDS)
    cache.set(stale_cache_key, copy.deepcopy(payload), YOUTUBE_STALE_CACHE_SECONDS)
    return Response(payload)


def _serialize_video(item: dict) -> dict:
    snippet = item.get("snippet", {})
    thumbnails = snippet.get("thumbnails", {})
    video_id = item.get("id", {}).get("videoId", "")

    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail_url": (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", ""),
        "description": snippet.get("description", ""),
        "embed_url": f"https://www.youtube.com/embed/{quote_plus(video_id)}" if video_id else "",
        "watch_url": f"https://www.youtube.com/watch?v={quote_plus(video_id)}" if video_id else "",
    }


def _normalize_query(query: str) -> str:
    normalized = re.sub(r"\s+", " ", (query or "").strip().lower())
    normalized = normalized[:MAX_QUERY_LENGTH].strip()
    if len(normalized) < MIN_QUERY_LENGTH:
        return ""
    return normalized


def _cache_payload(key: str, *, cache_type: str, fallback_reason: str = "") -> dict | None:
    payload = cache.get(key)
    if not payload:
        return None
    payload = copy.deepcopy(payload)
    payload["cache"] = True
    payload["cache_type"] = cache_type
    payload["fallback"] = False
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


def _make_youtube_cache_key(query: str) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:24]
    return f"youtube_search:v1:{digest}"


def _make_youtube_stale_cache_key(query: str) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:24]
    return f"youtube_search_stale:v1:{digest}"
