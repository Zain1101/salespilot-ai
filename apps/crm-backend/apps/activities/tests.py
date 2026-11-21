from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import Activity


User = get_user_model()


class ActivityAPITests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="activity-owner@example.com",
            password="SecureTest@2026!",
        )

        self.rep = User.objects.create_user(
            email="activity-rep@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="activity-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="activity-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Activities Test Organization",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Private Activities Organization",
            owner=self.outsider,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.rep,
            role=Membership.Role.SALES_REP,
        )

        self.viewer_membership = Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="AI Customer Inquiry",
            created_by=self.owner,
        )

        self.foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Private Lead",
            created_by=self.outsider,
        )

        self.url = reverse(
            "activity-list-create",
            kwargs={
                "organization_id": self.org.id,
            },
        )

        self.payload = {
            "activity_type": "call",
            "subject": "Customer discovery call",
            "description": "Discussed requirements.",
            "lead_id": str(self.lead.id),
        }

    def test_owner_can_log_activity(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Activity.objects.count(), 1)

        activity = Activity.objects.get()

        self.assertEqual(activity.organization, self.org)
        self.assertEqual(activity.created_by, self.owner)
        self.assertEqual(activity.lead, self.lead)

    def test_sales_rep_can_log_activity(self):
        self.client.force_authenticate(user=self.rep)

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(response.status_code, 201)

    def test_viewer_cannot_log_activity(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_read_activities(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            self.payload,
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_foreign_lead_rejected(self):
        self.client.force_authenticate(user=self.owner)

        payload = {
            **self.payload,
            "lead_id": str(self.foreign_lead.id),
        }

        response = self.client.post(
            self.url,
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Activity.objects.count(), 0)

    def test_missing_entity_rejected(self):
        self.client.force_authenticate(user=self.owner)

        payload = {
            "activity_type": "note",
            "subject": "Unlinked note",
        }

        response = self.client.post(
            self.url,
            payload,
        )

        self.assertEqual(response.status_code, 400)

    def test_multiple_entities_rejected(self):
        self.client.force_authenticate(user=self.owner)

        payload = {
            **self.payload,
            "company_id": str(uuid4()),
        }

        response = self.client.post(
            self.url,
            payload,
        )

        self.assertEqual(response.status_code, 400)

    def test_archived_lead_rejected(self):
        self.lead.is_archived = True
        self.lead.save(update_fields=["is_archived"])

        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            self.payload,
        )

        self.assertEqual(response.status_code, 400)

    def test_future_activity_rejected(self):
        self.client.force_authenticate(user=self.owner)

        payload = {
            **self.payload,
            "occurred_at": (
                timezone.now() + timedelta(days=1)
            ).isoformat(),
        }

        response = self.client.post(
            self.url,
            payload,
        )

        self.assertEqual(response.status_code, 400)

    def test_activity_type_filter(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            self.payload,
        )

        self.client.post(
            self.url,
            {
                **self.payload,
                "activity_type": "email",
                "subject": "Customer email",
            },
        )

        response = self.client.get(
            self.url,
            {"type": "call"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        self.assertEqual(
            response.data["results"][0]["activity_type"],
            "call",
        )

    def test_entity_filter(self):
        self.client.force_authenticate(user=self.owner)

        self.client.post(
            self.url,
            self.payload,
        )

        other_lead = Lead.objects.create(
            organization=self.org,
            title="Different Lead",
            created_by=self.owner,
        )

        self.client.post(
            self.url,
            {
                **self.payload,
                "lead_id": str(other_lead.id),
            },
        )

        response = self.client.get(
            self.url,
            {"lead_id": str(self.lead.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_outsider_cannot_read(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_member_cannot_read(self):
        self.viewer_membership.is_active = False
        self.viewer_membership.save(
            update_fields=["is_active"]
        )

        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_access_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_activity_cannot_be_patched(self):
        self.client.force_authenticate(user=self.owner)

        created = self.client.post(
            self.url,
            self.payload,
        )

        detail_url = reverse(
            "activity-detail",
            kwargs={
                "organization_id": self.org.id,
                "pk": created.data["id"],
            },
        )

        response = self.client.patch(
            detail_url,
            {"subject": "Modified subject"},
        )

        self.assertEqual(response.status_code, 405)

        activity = Activity.objects.get(
            pk=created.data["id"]
        )

        self.assertEqual(
            activity.subject,
            "Customer discovery call",
        )

    def test_cross_tenant_activity_not_listed(self):
        Activity.objects.create(
            organization=self.other_org,
            activity_type=Activity.Type.NOTE,
            subject="Private note",
            created_by=self.outsider,
            lead=self.foreign_lead,
        )

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)