from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.tenancy.permissions import IsTenantMember

from .serializers import SalesOverviewQuerySerializer
from .services import get_sales_overview


class SalesOverviewView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsTenantMember,
    ]

    def get(self, request, organization_id):

        serializer = SalesOverviewQuerySerializer(
            data=request.query_params
        )

        serializer.is_valid(raise_exception=True)

        currency = serializer.validated_data["currency"]

        result = get_sales_overview(
            organization_id=organization_id,
            currency=currency,
        )

        return Response(result)