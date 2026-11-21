from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from .models import Membership, OrganizationInvitation
from .services import create_organization, create_invitation


User = get_user_model()


class InvitationAcceptanceAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="SecureTest@2026!",
            email_verified=True,
        )

        self.employee = User.objects.create_user(
            email="employee@example.com",
            password="SecureTest@2026!",
            email_verified=True,
        )

        self.org = create_organization(
            name="Test Agency",
            owner=self.owner,
        )

        self.invitation, self.token = create_invitation(
            organization=self.org,
            invited_by=self.owner,
            email=self.employee.email,
            role=Membership.Role.SALES_REP,
        )

        self.url = reverse("accept-invitation")

    def test_verified_employee_can_accept(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.post(
            self.url,
            {"token": self.token},
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            Membership.objects.filter(
                organization=self.org,
                user=self.employee,
                role=Membership.Role.SALES_REP,
                is_active=True,
            ).exists()
        )

        self.invitation.refresh_from_db()

        self.assertEqual(
            self.invitation.status,
            OrganizationInvitation.Status.ACCEPTED,
        )

    def test_unverified_employee_cannot_accept(self):
        self.employee.email_verified = False
        self.employee.save(update_fields=["email_verified"])

        self.client.force_authenticate(user=self.employee)

        response = self.client.post(
            self.url,
            {"token": self.token},
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Membership.objects.filter(
                organization=self.org,
                user=self.employee,
            ).exists()
        )

    def test_invitation_cannot_be_reused(self):
        self.client.force_authenticate(user=self.employee)

        first_response = self.client.post(
            self.url,
            {"token": self.token},
        )

        second_response = self.client.post(
            self.url,
            {"token": self.token},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 400)

    def test_wrong_employee_cannot_accept(self):
        another_user = User.objects.create_user(
            email="different@example.com",
            password="SecureTest@2026!",
            email_verified=True,
        )

        self.client.force_authenticate(user=another_user)

        response = self.client.post(
            self.url,
            {"token": self.token},
        )

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_accept(self):
        response = self.client.post(
            self.url,
            {"token": self.token},
        )

        self.assertEqual(response.status_code, 401)