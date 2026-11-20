from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .models import Membership
from .services import create_organization


User = get_user_model()


class OrganizationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="TestPassword123!"
        )

    def test_create_organization(self):
        organization = create_organization(
            name="Test Company",
            owner=self.user
        )

        self.assertEqual(
            organization.name,
            "Test Company"
        )

        membership = Membership.objects.get(
            organization=organization,
            user=self.user
        )

        self.assertEqual(
            membership.role,
            Membership.Role.OWNER
        )

    def test_duplicate_membership_is_rejected(self):
        organization = create_organization(
            name="Test Company",
            owner=self.user
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    organization=organization,
                    user=self.user,
                    role=Membership.Role.VIEWER
                )

    def test_user_can_have_different_roles(self):
        org1 = create_organization(
            name="Company One",
            owner=self.user
        )

        another_owner = User.objects.create_user(
            email="another@example.com",
            password="TestPassword123!"
        )

        org2 = create_organization(
            name="Company Two",
            owner=another_owner
        )

        Membership.objects.create(
            organization=org2,
            user=self.user,
            role=Membership.Role.VIEWER
        )

        self.assertEqual(
            Membership.objects.get(
                organization=org1,
                user=self.user
            ).role,
            Membership.Role.OWNER
        )

        self.assertEqual(
            Membership.objects.get(
                organization=org2,
                user=self.user
            ).role,
            Membership.Role.VIEWER
        )