# Generated manually for FirstHome Navigator AI chat logging.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_coach", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AiChatLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notice_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("option_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("question", models.TextField()),
                ("answer", models.TextField(blank=True)),
                ("provider", models.CharField(default="template", max_length=40)),
                ("model_name", models.CharField(blank=True, max_length=80)),
                ("source_refs", models.JSONField(blank=True, default=list)),
                ("safety_flags", models.JSONField(blank=True, default=list)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["notice_id", "option_id", "created_at"], name="ai_coach_ai_notice__f6c1b1_idx")],
            },
        ),
    ]
