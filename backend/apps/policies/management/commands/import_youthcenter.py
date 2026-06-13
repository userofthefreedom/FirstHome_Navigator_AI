from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.policies.models import YouthPolicy
from apps.policies.services.youthcenter import (
    YouthCenterApiError,
    fetch_youthcenter_payload,
    normalize_youthcenter_policies,
)
from apps.rules.cache_service import clear_firsthome_cache


class Command(BaseCommand):
    help = "Import youth policies from the Ontong Youth open API."

    def add_arguments(self, parser):
        parser.add_argument("--page", type=int, default=1)
        parser.add_argument("--display", type=int)
        parser.add_argument(
            "--max-pages",
            type=int,
            help="Maximum pages to fetch. Defaults to 1 page for dry-run and 4 pages for import.",
        )
        parser.add_argument("--query", default="")
        parser.add_argument("--keyword", default="")
        parser.add_argument("--clear", action="store_true", help="Delete existing youth policies before importing.")
        parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize policies without writing to DB.")

    def handle(self, *args, **options):
        api_key = settings.EXTERNAL_API_KEYS.get("YOUTH_POLICY_API_KEY", "")
        if not api_key:
            raise CommandError("YOUTH_POLICY_API_KEY is missing. Add it to backend/.env after Ontong Youth approves it.")

        display = options["display"] or (20 if options["dry_run"] else 50)
        max_pages = options["max_pages"] if options["max_pages"] is not None else (1 if options["dry_run"] else 4)
        if max_pages <= 0:
            raise CommandError("--max-pages must be greater than 0 for import_youthcenter.")

        policies = []
        seen_keys = set()
        try:
            for page in range(options["page"], options["page"] + max_pages):
                payload = fetch_youthcenter_payload(
                    api_key,
                    page=page,
                    display=display,
                    query=options["query"],
                    keyword=options["keyword"],
                )
                page_policies = normalize_youthcenter_policies(payload)
                for policy in page_policies:
                    key = (policy.provider, policy.name)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    policies.append(policy)
                if len(page_policies) < display:
                    break
        except YouthCenterApiError as exc:
            raise CommandError(str(exc)) from exc

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fetched {len(policies)} youth policies from {max_pages} page(s), display={display}. No database changes."
                )
            )
            for policy in policies[:5]:
                self.stdout.write(f"- {policy.provider} {policy.name}")
            return

        if options["clear"]:
            YouthPolicy.objects.all().delete()

        created_count = 0
        updated_count = 0
        for policy in policies:
            _instance, created = YouthPolicy.objects.update_or_create(
                provider=policy.provider,
                name=policy.name,
                defaults={
                    "target": policy.target,
                    "benefit": policy.benefit,
                    "policy_category": policy.policy_category,
                    "regions": policy.regions,
                    "age_min": policy.age_min,
                    "age_max": policy.age_max,
                    "max_income": policy.max_income,
                    "requires_homeless": policy.requires_homeless,
                    "source_url": policy.source_url,
                    "reasons": policy.reasons,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported youth policies: {created_count} created, {updated_count} updated "
                f"from {max_pages} page(s), display={display}."
            )
        )
        clear_firsthome_cache()
