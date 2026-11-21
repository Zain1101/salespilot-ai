from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from .models import Membership
from .services import create_organization


User = get_user_model()


class MemberAPITests(APITestCase):

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

        self.organization = create_organization(
            name="Test Agency",
            owner=self.owner,
        )

        self.employee_membership = Membership.objects.create(
            organization=self.organization,
            user=self.employee,
            role=Membership.Role.SALES_REP,
        )

        self.list_url = reverse(
            "organization-members",
            kwargs={
                "organization_id": self.organization.id,
            },
        )

    def test_owner_can_list_members(self):

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_employee_can_view_members(self):

        self.client.force_authenticate(user=self.employee)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_view_members(self):

        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_view_members(self):

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_member_detail(self):

        self.client.force_authenticate(user=self.owner)

        url = reverse(
            "organization-member-detail",
            kwargs={
                "organization_id": self.organization.id,
                "pk": self.employee_membership.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["role"],
            Membership.Role.SALES_REP,
        )

    def test_other_organization_member_not_accessible(self):

        second_org = create_organization(
            name="Second Agency",
            owner=self.outsider,
        )

        other_membership = Membership.objects.get(
            organization=second_org,
            user=self.outsider,
        )

        self.client.force_authenticate(user=self.owner)

        url = reverse(
            "organization-member-detail",
            kwargs={
                "organization_id": self.organization.id,
                "pk": other_membership.id,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_inactive_member_cannot_list_members(self):

        self.employee_membership.is_active = False
        self.employee_membership.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.employee)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)