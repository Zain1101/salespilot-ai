import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Pipeline(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="sales_pipelines",
    )

    name = models.CharField(max_length=150)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_sales_pipelines",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(is_default=True),
                name="unique_default_pipeline_per_org",
            ),
        ]

    def __str__(self):
        return self.name


class PipelineStage(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="stages",
    )

    name = models.CharField(max_length=100)

    position = models.PositiveIntegerField()

    probability = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "position"],
                name="unique_stage_position_per_pipeline",
            ),
            models.CheckConstraint(
                condition=Q(probability__lte=100),
                name="pipeline_stage_probability_lte_100",
            ),
        ]

    def __str__(self):
        return f"{self.pipeline.name}: {self.name}"