from __future__ import annotations

import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response


DEFAULT_QUERY = "청약 공공분양 주택청약 내집마련"


@api_view(["GET"])
def default_videos_view(_request):
    return _youtube_response(DEFAULT_QUERY)


@api_view(["GET"])
def search_videos_view(request):
    query = request.query_params.get("q", "").strip() or "청약"
    return _youtube_response(query)


def _youtube_response(query: str):
    api_key = settings.EXTERNAL_API_KEYS.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return Response({"items": [], "fallback": True, "fallback_reason": "YouTube API 키가 없어 영상을 불러오지 못했습니다. backend/.env의 YOUTUBE_API_KEY를 확인해 주세요."})
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 6,
                "key": api_key,
                "safeSearch": "moderate",
                "relevanceLanguage": "ko",
                "regionCode": "KR",
                "order": "relevance",
            },
            timeout=10,
        )
        response.raise_for_status()
        items = [_serialize_video(item) for item in response.json().get("items", []) if item.get("id", {}).get("videoId")]
    except requests.RequestException as exc:
        return Response({"items": [], "fallback": True, "fallback_reason": f"YouTube API 응답을 받지 못했습니다. 키, 할당량, 호출 허용 설정을 확인해 주세요. ({exc.response.status_code if exc.response else 'network'})"})
    if not items:
        return Response({"items": [], "fallback": True, "fallback_reason": "청약 관련 영상 검색 결과가 없습니다. 검색어를 바꿔 다시 시도해 주세요."})
    return Response({"items": items, "fallback": False})


def _serialize_video(item: dict) -> dict:
    snippet = item.get("snippet", {})
    thumbnails = snippet.get("thumbnails", {})
    return {
        "video_id": item.get("id", {}).get("videoId", ""),
        "title": snippet.get("title", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail_url": (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", ""),
        "description": snippet.get("description", ""),
    }
