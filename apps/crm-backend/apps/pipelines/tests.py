from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Pipeline, PipelineStage


User = get_user_model()


class PipelineAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="pipeline-owner@example.com",
            password="SecureTest@2026!",
        )

        self.admin = User.objects.create_user(
            email="pipeline-admin@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="pipeline-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="pipeline-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Pipeline Test Agency",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Other Pipeline Agency",
            owner=self.outsider,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.admin,
            role=Membership.Role.ADMIN,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.url = reverse(
            "pipeline-list-create",
            kwargs={"organization_id": self.org.id},
        )

    def test_owner_creates_pipeline_and_stages(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"name": "Default Sales Pipeline"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_default"])
        self.assertEqual(len(response.data["stages"]), 5)

        pipeline = Pipeline.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(pipeline.organization, self.org)
        self.assertEqual(
            PipelineStage.objects.filter(
                pipeline=pipeline
            ).count(),
            5,
        )

    def test_admin_can_create_pipeline(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            {"name": "Enterprise Sales"},
        )

        self.assertEqual(response.status_code, 201)

    def test_viewer_cannot_create_pipeline(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            {"name": "Unauthorized Pipeline"},
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_list_pipelines(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            {"name": "Default Sales Pipeline"},
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_first_pipeline_is_default(self):
        self.client.force_authenticate(user=self.owner)

        first = self.client.post(
            self.url,
            {"name": "First Pipeline"},
        )

        second = self.client.post(
            self.url,
            {"name": "Second Pipeline"},
        )

        self.assertTrue(first.data["is_default"])
        self.assertFalse(second.data["is_default"])

        self.assertEqual(
            Pipeline.objects.filter(
                organization=self.org,
                is_default=True,
            ).count(),
            1,
        )

    def test_duplicate_pipeline_is_rejected(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            {"name": "Enterprise Sales"},
        )

        response = self.client.post(
            self.url,
            {"name": "enterprise sales"},
        )

        self.assertEqual(response.status_code, 400)

    def test_outsider_cannot_access_pipelines(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_pipeline_detail_hidden(self):
        self.client.force_authenticate(user=self.outsider)

        foreign_url = reverse(
            "pipeline-list-create",
            kwargs={
                "organization_id": self.other_org.id
            },
        )

        created = self.client.post(
            foreign_url,
            {"name": "Private Pipeline"},
        )

        pipeline_id = created.data["id"]

        self.client.force_authenticate(user=self.owner)

        detail_url = reverse(
            "pipeline-detail",
            kwargs={
                "organization_id": self.org.id,
                "pk": pipeline_id,
            },
        )

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_access_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)