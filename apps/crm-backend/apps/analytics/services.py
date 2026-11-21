from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q, Sum

from apps.opportunities.models import Opportunity


ZERO = Decimal("0.00")
ONE_HUNDRED = Decimal("100")


def money(value):
    """Format Decimal values as two-decimal strings."""
    if value is None:
        value = ZERO

    return str(
        Decimal(value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def percentage(numerator, denominator):
    """Calculate a percentage without division by zero."""
    if denominator == 0:
        return money(ZERO)

    result = (
        Decimal(numerator)
        / Decimal(denominator)
    ) * ONE_HUNDRED

    return money(result)


def get_sales_overview(*, organization_id, currency):
    """
    Compute tenant-scoped sales analytics.

    Assumes the API layer has already authorized
    active membership in the organization.
    """

    opportunities = Opportunity.objects.filter(
        organization_id=organization_id,
        currency=currency,
    )

    # Count opportunities by lifecycle status.
    counts = opportunities.aggregate(
        total=Count("id"),
        open=Count(
            "id",
            filter=Q(status=Opportunity.Status.OPEN),
        ),
        won=Count(
            "id",
            filter=Q(status=Opportunity.Status.WON),
        ),
        lost=Count(
            "id",
            filter=Q(status=Opportunity.Status.LOST),
        ),
    )

    open_opportunities = opportunities.filter(
        status=Opportunity.Status.OPEN,
    )

    open_value = open_opportunities.aggregate(
        total=Sum("estimated_value"),
    )["total"] or ZERO

    won_opportunities = opportunities.filter(
        status=Opportunity.Status.WON,
    )

    won_metrics = won_opportunities.aggregate(
        revenue=Sum("actual_value"),
        missing_actual_value=Count(
            "id",
            filter=Q(actual_value__isnull=True),
        ),
    )

    won_revenue = won_metrics["revenue"] or ZERO

    lost_value = opportunities.filter(
        status=Opportunity.Status.LOST,
    ).aggregate(
        total=Sum("estimated_value"),
    )["total"] or ZERO

    # Group open opportunities by their actual
    # pipeline and stage identifiers.
    stage_rows = (
        open_opportunities
        .values(
            "pipeline_id",
            "pipeline__name",
            "stage_id",
            "stage__name",
            "stage__position",
            "stage__probability",
        )
        .annotate(
            deal_count=Count("id"),
            total_value=Sum("estimated_value"),
        )
        .order_by(
            "pipeline__name",
            "stage__position",
            "stage__name",
            "stage_id",
        )
    )

    stages = []
    weighted_total = ZERO
    unassigned_count = 0

    for row in stage_rows:
        stage_value = row["total_value"] or ZERO
        probability = row["stage__probability"] or 0

        weighted_value = (
            stage_value
            * Decimal(probability)
            / ONE_HUNDRED
        )

        weighted_total += weighted_value

        if row["stage_id"] is None:
            unassigned_count += row["deal_count"]

        stages.append({
            "pipeline_id": (
                str(row["pipeline_id"])
                if row["pipeline_id"]
                else None
            ),
            "pipeline_name": row["pipeline__name"],
            "stage_id": (
                str(row["stage_id"])
                if row["stage_id"]
                else None
            ),
            "stage_name": (
                row["stage__name"] or "Unassigned"
            ),
            "stage_position": row["stage__position"],
            "probability": probability,
            "deal_count": row["deal_count"],
            "total_value": money(stage_value),
            "weighted_value": money(weighted_value),
        })

    closed_count = counts["won"] + counts["lost"]

    return {
        "currency": currency,

        "counts": {
            "total": counts["total"],
            "open": counts["open"],
            "won": counts["won"],
            "lost": counts["lost"],
            "closed": closed_count,
        },

        "revenue": {
            "won_revenue": money(won_revenue),
            "open_pipeline_value": money(open_value),
            "weighted_open_value": money(weighted_total),
            "lost_estimated_value": money(lost_value),
        },

        "performance": {
            "win_rate_percentage": percentage(
                counts["won"],
                closed_count,
            ),
        },

        "data_quality": {
            "open_without_stage": unassigned_count,
            "won_without_actual_value": (
                won_metrics["missing_actual_value"]
            ),
        },

        "stages": stages,
    }