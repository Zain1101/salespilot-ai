from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization

from .models import SalesTask, SalesTaskStatusHistory


User = get_user_model()


class SalesTaskTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="task-owner@example.com",
            password="SecureTest@2026!",
        )

        self.rep = User.objects.create_user(
            email="task-rep@example.com",
            password="SecureTest@2026!",
        )

        self.viewer = User.objects.create_user(
            email="task-viewer@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="task-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Task Testing Organization",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Private Task Organization",
            owner=self.outsider,
        )

        self.rep_membership = Membership.objects.create(
            organization=self.org,
            user=self.rep,
            role=Membership.Role.SALES_REP,
        )

        Membership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

        self.foreign_membership = Membership.objects.get(
            organization=self.other_org,
            user=self.outsider,
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="Follow-up Lead",
            created_by=self.owner,
        )

        self.foreign_lead = Lead.objects.create(
            organization=self.other_org,
            title="Private Lead",
            created_by=self.outsider,
        )

        self.url = reverse(
            "sales-task-list-create",
            kwargs={"organization_id": self.org.id},
        )

        self.payload = {
            "title": "Follow up with customer",
            "description": "Discuss the commercial proposal.",
            "assigned_to_id": str(self.rep_membership.id),
            "due_at": (
                timezone.now() + timedelta(days=1)
            ).isoformat(),
            "priority": "high",
            "lead_id": str(self.lead.id),
        }

    def create_task(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def status_url(self, task_id):
        return reverse(
            "sales-task-status",
            kwargs={
                "organization_id": self.org.id,
                "pk": task_id,
            },
        )

    def test_owner_can_create_task(self):
        self.create_task()

        self.assertEqual(SalesTask.objects.count(), 1)

        task = SalesTask.objects.get()
        self.assertEqual(task.status, SalesTask.Status.PENDING)
        self.assertEqual(task.assigned_to, self.rep_membership)

    def test_sales_rep_can_create_own_task(self):
        self.client.force_authenticate(user=self.rep)

        response = self.client.post(self.url, self.payload)

        self.assertEqual(response.status_code, 201)

    def test_sales_rep_cannot_assign_another_member(self):
        owner_membership = Membership.objects.get(
            organization=self.org,
            user=self.owner,
        )

        self.client.force_authenticate(user=self.rep)

        response = self.client.post(
            self.url,
            {
                **self.payload,
                "assigned_to_id": str(owner_membership.id),
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_create_task(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(self.url, self.payload)

        self.assertEqual(response.status_code, 403)

    def test_foreign_assignee_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                **self.payload,
                "assigned_to_id": str(self.foreign_membership.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_foreign_lead_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                **self.payload,
                "lead_id": str(self.foreign_lead.id),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_past_due_date_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                **self.payload,
                "due_at": (
                    timezone.now() - timedelta(days=1)
                ).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_multiple_entity_links_rejected(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {
                **self.payload,
                "contact_id": str(uuid4()),
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_assigned_rep_can_complete_task(self):
        task_id = self.create_task()

        self.client.force_authenticate(user=self.rep)

        response = self.client.post(
            self.status_url(task_id),
            {
                "status": "completed",
                "reason": "Customer contacted.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["changed"])

        task = SalesTask.objects.get(pk=task_id)
        self.assertEqual(task.status, SalesTask.Status.COMPLETED)
        self.assertEqual(task.completed_by, self.rep)
        self.assertIsNotNone(task.completed_at)

        self.assertEqual(
            SalesTaskStatusHistory.objects.count(), 1
        )

    def test_duplicate_completion_is_idempotent(self):
        task_id = self.create_task()

        url = self.status_url(task_id)

        first = self.client.post(
            url,
            {"status": "completed"},
        )

        second = self.client.post(
            url,
            {"status": "completed"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["changed"])

        self.assertEqual(
            SalesTaskStatusHistory.objects.count(), 1
        )

    def test_manager_role_can_cancel_task(self):
        task_id = self.create_task()

        response = self.client.post(
            self.status_url(task_id),
            {
                "status": "cancelled",
                "reason": "Customer no longer requires follow-up.",
            },
        )

        self.assertEqual(response.status_code, 200)

        task = SalesTask.objects.get(pk=task_id)
        self.assertEqual(task.status, SalesTask.Status.CANCELLED)

    def test_sales_rep_cannot_cancel_task(self):
        task_id = self.create_task()

        self.client.force_authenticate(user=self.rep)

        response = self.client.post(
            self.status_url(task_id),
            {"status": "cancelled"},
        )

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_read_tasks(self):
        self.create_task()
        self.client.force_authenticate(user=self.viewer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_my_tasks_filter(self):
        self.create_task()
        self.client.force_authenticate(user=self.rep)

        response = self.client.get(
            self.url,
            {"mine": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_outsider_cannot_read_tasks(self):
        self.client.force_authenticate(user=self.outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_access_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)