from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Membership, MembershipStatusAudit
from .services import create_organization

User = get_user_model()


class MemberStatusTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="SecureTest@2026!",
        )
        self.employee = User.objects.create_user(
            email="employee@example.com",
            password="SecureTest@2026!",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Test Organization",
            owner=self.owner,
        )

        self.membership = Membership.objects.create(
            organization=self.org,
            user=self.employee,
            role=Membership.Role.SALES_REP,
        )

        self.deactivate_url = reverse(
            "deactivate-member",
            kwargs={
                "organization_id": self.org.id,
                "member_id": self.membership.id,
            },
        )

        self.reactivate_url = reverse(
            "reactivate-member",
            kwargs={
                "organization_id": self.org.id,
                "member_id": self.membership.id,
            },
        )

    def test_owner_can_deactivate_employee(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.deactivate_url)

        self.assertEqual(response.status_code, 200)

        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_active)

        self.assertEqual(
            MembershipStatusAudit.objects.count(),
            1,
        )

    def test_owner_can_reactivate_employee(self):
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(self.reactivate_url)

        self.assertEqual(response.status_code, 200)

        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)

    def test_outsider_cannot_deactivate(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(self.deactivate_url)

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_deactivate_self(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.post(self.deactivate_url)

        self.assertEqual(response.status_code, 403)

    def test_owner_cannot_be_deactivated(self):
        owner_membership = Membership.objects.get(
            organization=self.org,
            user=self.owner,
        )

        self.client.force_authenticate(user=self.owner)

        url = reverse(
            "deactivate-member",
            kwargs={
                "organization_id": self.org.id,
                "member_id": owner_membership.id,
            },
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_repeated_deactivation_does_not_duplicate_audit(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(self.deactivate_url)
        self.client.post(self.deactivate_url)

        self.assertEqual(
            MembershipStatusAudit.objects.count(),
            1,
        )