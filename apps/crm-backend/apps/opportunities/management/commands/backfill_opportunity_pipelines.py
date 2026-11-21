from django.core.management.base import BaseCommand
from django.db import transaction

from apps.opportunities.models import Opportunity
from apps.pipelines.models import Pipeline, PipelineStage


class Command(BaseCommand):
    help = "Assign default pipelines and first stages to old opportunities."

    def handle(self, *args, **options):

        organization_ids = (
            Opportunity.objects
            .filter(pipeline__isnull=True, stage__isnull=True)
            .values_list("organization_id", flat=True)
            .distinct()
        )

        updated = 0
        skipped = 0

        for organization_id in organization_ids:

            with transaction.atomic():

                # Match the organization-first locking
                # convention used by conversion.
                from apps.organizations.models import Organization

                organization = (
                    Organization.objects
                    .select_for_update()
                    .get(pk=organization_id)
                )

                pipeline = Pipeline.objects.filter(
                    organization=organization,
                    is_default=True,
                    is_active=True,
                ).first()

                if pipeline is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped organization {organization_id}: "
                            "no active default pipeline."
                        )
                    )
                    skipped += 1
                    continue

                first_stage = PipelineStage.objects.filter(
                    pipeline=pipeline
                ).order_by("position", "id").first()

                if first_stage is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped organization {organization_id}: "
                            "no pipeline stages."
                        )
                    )
                    skipped += 1
                    continue

                count = Opportunity.objects.filter(
                    organization=organization,
                    pipeline__isnull=True,
                    stage__isnull=True,
                ).update(
                    pipeline=pipeline,
                    stage=first_stage,
                )

                updated += count

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill finished: {updated} opportunities updated; "
                f"{skipped} organizations skipped."
            )
        )