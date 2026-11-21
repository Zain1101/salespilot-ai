from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserSerializer

from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import VerifyEmailSerializer

from .verification_services import (
    request_email_verification,
    verify_email,
)

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class RequestEmailVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request_email_verification(user=request.user)
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Verification email generated. "
                    "Check your email."
                )
            },
            status=status.HTTP_200_OK,
        )


class ConfirmEmailVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_email(
                user=request.user,
                token=serializer.validated_data["token"],
            )
        except ValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )