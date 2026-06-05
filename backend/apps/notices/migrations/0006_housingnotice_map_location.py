from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notices", "0005_backfill_service_target_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="housingnotice",
            name="geocode_quality",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="housingnotice",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="housingnotice",
            name="location_label",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="housingnotice",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
