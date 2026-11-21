from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from .models import Membership, OrganizationInvitation
from .services import create_organization


User = get_user_model()


class InvitationAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Test Agency",
            owner=self.owner,
        )

        self.url = reverse(
            "organization-invitations",
            kwargs={"organization_id": self.org.id},
        )

    def test_owner_can_create_invitation(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "email": "employee@example.com",
                "role": Membership.Role.SALES_REP,
            },
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            OrganizationInvitation.objects.filter(
                organization=self.org,
                email="employee@example.com",
            ).exists()
        )

        self.assertNotIn("token_hash", response.data)

    def test_outsider_cannot_invite(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.post(
            self.url,
            {
                "email": "employee@example.com",
                "role": Membership.Role.SALES_REP,
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_owner_role_cannot_be_invited(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                "email": "employee@example.com",
                "role": Membership.Role.OWNER,
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_invite_is_blocked(self):
        response = self.client.post(
            self.url,
            {
                "email": "employee@example.com",
                "role": Membership.Role.SALES_REP,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_owner_can_revoke_invitation(self):
        self.client.force_authenticate(user=self.owner)

        create_response = self.client.post(
            self.url,
            {
                "email": "employee@example.com",
                "role": Membership.Role.SALES_REP,
            },
        )

        self.assertEqual(create_response.status_code, 201)

        invitation_id = create_response.data["id"]

        revoke_url = reverse(
            "revoke-invitation",
            kwargs={
                "organization_id": self.org.id,
                "invitation_id": invitation_id,
            },
        )

        response = self.client.post(revoke_url)

        self.assertEqual(response.status_code, 200)

        invitation = OrganizationInvitation.objects.get(
            id=invitation_id
        )

        self.assertEqual(
            invitation.status,
            OrganizationInvitation.Status.REVOKED,
        )