from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from common.tenancy.services import (
    get_active_membership,
    require_organization_role,
)


User = get_user_model()


class TenantSecurityTests(TestCase):

    def setUp(self):
        self.owner_a = User.objects.create_user(
            email="owner-a@example.com",
            password="SecureTest@2026!",
        )

        self.owner_b = User.objects.create_user(
            email="owner-b@example.com",
            password="SecureTest@2026!",
        )

        self.org_a = create_organization(
            name="Company A",
            owner=self.owner_a,
        )

        self.org_b = create_organization(
            name="Company B",
            owner=self.owner_b,
        )

        self.employee = User.objects.create_user(
            email="employee@example.com",
            password="SecureTest@2026!",
        )

        self.membership = Membership.objects.create(
            organization=self.org_a,
            user=self.employee,
            role=Membership.Role.SALES_REP,
        )

    def test_member_can_access_own_organization(self):
        result = get_active_membership(
            user=self.employee,
            organization_id=self.org_a.id,
        )

        self.assertEqual(result, self.membership)

    def test_member_cannot_access_other_organization(self):
        with self.assertRaises(PermissionDenied):
            get_active_membership(
                user=self.employee,
                organization_id=self.org_b.id,
            )

    def test_inactive_membership_is_rejected(self):
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            get_active_membership(
                user=self.employee,
                organization_id=self.org_a.id,
            )

    def test_sales_rep_cannot_access_admin_operations(self):
        with self.assertRaises(PermissionDenied):
            require_organization_role(
                user=self.employee,
                organization_id=self.org_a.id,
                allowed_roles=[
                    Membership.Role.OWNER,
                    Membership.Role.ADMIN,
                ],
            )

    def test_owner_can_access_admin_operations(self):
        result = require_organization_role(
            user=self.owner_a,
            organization_id=self.org_a.id,
            allowed_roles=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        )

        self.assertEqual(result.role, Membership.Role.OWNER)

    def test_inactive_organization_is_rejected(self):
        self.org_a.is_active = False
        self.org_a.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            get_active_membership(
                user=self.employee,
                organization_id=self.org_a.id,
            )

    def test_globally_inactive_user_is_rejected(self):
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])

        with self.assertRaises(PermissionDenied):
            get_active_membership(
                user=self.employee,
                organization_id=self.org_a.id,
            )