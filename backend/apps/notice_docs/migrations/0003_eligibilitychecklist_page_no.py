from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notice_docs", "0002_expand_payment_schedule_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="eligibilitychecklist",
            name="page_no",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
