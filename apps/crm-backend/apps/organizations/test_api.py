from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from .models import Organization, Membership
from .services import create_organization


User = get_user_model()


class OrganizationAPITests(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="owner1@example.com",
            password="SecureTest@2026!",
        )

        self.user2 = User.objects.create_user(
            email="owner2@example.com",
            password="SecureTest@2026!",
        )

        self.org1 = create_organization(
            name="Company One",
            owner=self.user1,
        )

        self.org2 = create_organization(
            name="Company Two",
            owner=self.user2,
        )

    def test_create_organization(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            reverse("organization-list-create"),
            {
                "name": "New Agency",
                "timezone": "Asia/Karachi",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        organization = Organization.objects.get(
            id=response.data["id"]
        )

        self.assertTrue(
            Membership.objects.filter(
                organization=organization,
                user=self.user1,
                role=Membership.Role.OWNER,
                is_active=True,
            ).exists()
        )

    def test_user_only_sees_own_organizations(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse("organization-list-create")
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = {
            item["id"] for item in response.data
        }

        self.assertIn(str(self.org1.id), returned_ids)
        self.assertNotIn(str(self.org2.id), returned_ids)

    def test_cannot_access_other_organization(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse(
                "organization-detail",
                kwargs={"pk": self.org2.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_access_is_blocked(self):
        response = self.client.get(
            reverse("organization-list-create")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_inactive_membership_cannot_access_org(self):
        Membership.objects.filter(
            user=self.user1,
            organization=self.org1,
        ).update(is_active=False)

        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse(
                "organization-detail",
                kwargs={"pk": self.org1.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_inactive_organization_is_hidden(self):
        self.org1.is_active = False
        self.org1.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse("organization-list-create")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_invalid_timezone_is_rejected(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            reverse("organization-list-create"),
            {
                "name": "Another Agency",
                "timezone": "Invalid/Timezone",
            },
        )

        self.assertEqual(response.status_code, 400)
        