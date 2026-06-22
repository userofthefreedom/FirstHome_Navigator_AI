from django.db import migrations, models


def backfill_region_fields(apps, schema_editor):
    MarketAssetPrice = apps.get_model("market", "MarketAssetPrice")
    for item in MarketAssetPrice.objects.all():
        meta = item.source_meta or {}
        region_code = str(meta.get("lawd_cd") or meta.get("region_code") or "")
        region_name = str(meta.get("region_name") or meta.get("label") or "")
        if " 아파트 평균" in region_name:
            region_name = region_name.split(" 아파트 평균", 1)[0]
        item.region_code = region_code
        item.region_name = region_name
        item.save(update_fields=["region_code", "region_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="marketassetprice",
            name="unique_market_asset_price",
        ),
        migrations.AddField(
            model_name="marketassetprice",
            name="region_code",
            field=models.CharField(blank=True, db_index=True, max_length=10),
        ),
        migrations.AddField(
            model_name="marketassetprice",
            name="region_name",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.RunPython(backfill_region_fields, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="marketassetprice",
            constraint=models.UniqueConstraint(fields=("asset_type", "base_date", "region_code"), name="unique_market_asset_price"),
        ),
    ]
