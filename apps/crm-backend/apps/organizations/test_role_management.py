from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from .models import Membership, MembershipRoleAudit
from .services import create_organization


User = get_user_model()


class RoleManagementTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="SecureTest@2026!",
        )

        self.admin = User.objects.create_user(
            email="admin@example.com",
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

        self.admin_membership = Membership.objects.create(
            organization=self.org,
            user=self.admin,
            role=Membership.Role.ADMIN,
        )

        self.employee_membership = Membership.objects.create(
            organization=self.org,
            user=self.employee,
            role=Membership.Role.SALES_REP,
        )

        self.url = reverse(
            "update-member-role",
            kwargs={
                "organization_id": self.org.id,
                "member_id": self.employee_membership.id,
            },
        )

    def test_owner_can_promote_employee(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 200)

        self.employee_membership.refresh_from_db()
        self.assertEqual(
            self.employee_membership.role,
            Membership.Role.MANAGER,
        )

        self.assertTrue(
            MembershipRoleAudit.objects.filter(
                membership=self.employee_membership,
                old_role=Membership.Role.SALES_REP,
                new_role=Membership.Role.MANAGER,
                changed_by=self.owner,
            ).exists()
        )

    def test_admin_can_change_sales_rep_role(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_cannot_promote_to_admin(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.url,
            {"role": "admin"},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_change_other_admin(self):
        second_admin = User.objects.create_user(
            email="secondadmin@example.com",
            password="SecureTest@2026!",
        )

        target = Membership.objects.create(
            organization=self.org,
            user=second_admin,
            role=Membership.Role.ADMIN,
        )

        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "update-member-role",
            kwargs={
                "organization_id": self.org.id,
                "member_id": target.id,
            },
        )

        response = self.client.patch(
            url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 403)

    def test_user_cannot_change_own_role(self):
        self.client.force_authenticate(user=self.admin)

        url = reverse(
            "update-member-role",
            kwargs={
                "organization_id": self.org.id,
                "member_id": self.admin_membership.id,
            },
        )

        response = self.client.patch(
            url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 403)

    def test_sales_rep_cannot_change_roles(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.patch(
            self.url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_change_roles(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.patch(
            self.url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 403)

    def test_owner_role_cannot_be_assigned(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            self.url,
            {"role": "owner"},
        )

        self.assertEqual(response.status_code, 400)

    def test_role_change_is_idempotent(self):
        self.client.force_authenticate(user=self.owner)

        self.client.patch(
            self.url,
            {"role": "sales_rep"},
        )

        self.assertEqual(
            MembershipRoleAudit.objects.count(),
            0,
        )

    def test_unauthenticated_user_is_rejected(self):
        response = self.client.patch(
            self.url,
            {"role": "manager"},
        )

        self.assertEqual(response.status_code, 401)
        