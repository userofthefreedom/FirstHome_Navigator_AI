from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


FIXTURE_PATH = settings.BASE_DIR / "fixtures" / "firsthome_mvp.json"


@lru_cache(maxsize=1)
def load_fixture() -> dict[str, Any]:
    with Path(FIXTURE_PATH).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def default_profile() -> dict[str, Any]:
    return load_fixture()["profile"].copy()


def sample_profiles() -> list[dict[str, Any]]:
    return [profile.copy() for profile in load_fixture().get("sample_profiles", [])]


def notices() -> list[dict[str, Any]]:
    return [notice.copy() for notice in load_fixture()["notices"]]


def products() -> list[dict[str, Any]]:
    return [product.copy() for product in load_fixture()["products"]]


def policies() -> list[dict[str, Any]]:
    return [policy.copy() for policy in load_fixture()["policies"]]


def find_notice(notice_id: int) -> dict[str, Any] | None:
    return next((notice for notice in notices() if notice["id"] == notice_id), None)
