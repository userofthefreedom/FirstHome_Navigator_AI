from django.db import migrations


DENY_KEYWORDS = [
    "임대",
    "행복주택",
    "국민임대",
    "영구임대",
    "매입임대",
    "전세",
    "장기전세",
    "든든전세",
    "분양전환",
    "10년공공임대",
    "10년 공공임대",
    "청년 공공주택",
    "일반매각",
    "유주택자 계약 가능",
    "유주택자 계약가능",
    "분양광고",
    "오피스텔 분양광고",
]


def classify_notice(notice):
    text = " ".join(
        str(value)
        for value in [
            notice.title,
            notice.supply_type,
            notice.housing_type,
            notice.provider,
            notice.district,
            " ".join(str(tag) for tag in (notice.tags or [])),
        ]
        if value
    )
    normalized = text.replace(" ", "")

    for keyword in DENY_KEYWORDS:
        if keyword in text or keyword.replace(" ", "") in normalized:
            return "excluded", False, f"서비스 범위 밖 공고: {keyword}"

    if "신혼희망타운" in text and "공공분양" in text:
        return "newlywed_public_sale", True, ""
    if "민간참여형" in text and "공공분양" in text:
        return "private_participation_public_sale", True, ""
    if "공공분양주택" in normalized or "공공분양" in text or "뉴홈" in text:
        return "public_sale", True, ""
    return "unknown", False, "소유형 공공분양 여부 확인 필요"


def backfill_service_target_fields(apps, _schema_editor):
    HousingNotice = apps.get_model("notices", "HousingNotice")
    for notice in HousingNotice.objects.all():
        ownership_type, is_service_target, exclude_reason = classify_notice(notice)
        notice.ownership_type = ownership_type
        notice.is_service_target = is_service_target
        notice.exclude_reason = exclude_reason
        notice.save(update_fields=["ownership_type", "is_service_target", "exclude_reason"])


class Migration(migrations.Migration):

    dependencies = [
        ("notices", "0004_housingnotice_exclude_reason_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_service_target_fields, migrations.RunPython.noop),
    ]
