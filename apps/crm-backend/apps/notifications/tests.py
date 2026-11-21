from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.leads.models import Lead
from apps.organizations.models import Membership
from apps.organizations.services import create_organization
from apps.tasks.models import SalesTask

from .models import Notification
from .services import process_task_reminders


User = get_user_model()


class NotificationTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="notification-owner@example.com",
            password="SecureTest@2026!",
        )

        self.outsider = User.objects.create_user(
            email="notification-outsider@example.com",
            password="SecureTest@2026!",
        )

        self.org = create_organization(
            name="Notification Test Org",
            owner=self.owner,
        )

        self.other_org = create_organization(
            name="Private Notification Org",
            owner=self.outsider,
        )

        self.membership = Membership.objects.get(
            organization=self.org,
            user=self.owner,
        )

        self.lead = Lead.objects.create(
            organization=self.org,
            title="Reminder Test Lead",
            created_by=self.owner,
        )

        self.list_url = reverse(
            "notification-list",
            kwargs={
                "organization_id": self.org.id,
            },
        )

        self.count_url = reverse(
            "notification-unread-count",
            kwargs={
                "organization_id": self.org.id,
            },
        )

        self.client.force_authenticate(
            user=self.owner
        )

    def create_task(
        self,
        *,
        hours_until_due=1,
        status=SalesTask.Status.PENDING,
        assigned_to=None,
    ):
        return SalesTask.objects.create(
            organization=self.org,
            title="Call customer",
            created_by=self.owner,
            assigned_to=assigned_to or self.membership,
            lead=self.lead,
            due_at=(
                timezone.now()
                + timedelta(hours=hours_until_due)
            ),
            status=status,
        )

    def test_due_soon_notification_created(self):
        self.create_task(hours_until_due=1)

        result = process_task_reminders()

        self.assertEqual(
            result["due_soon_created"], 1
        )
        self.assertEqual(
            Notification.objects.count(), 1
        )
        self.assertEqual(
            Notification.objects.get().notification_type,
            Notification.Type.TASK_DUE_SOON,
        )

    def test_overdue_notification_created(self):
        self.create_task(hours_until_due=-1)

        result = process_task_reminders()

        self.assertEqual(
            result["overdue_created"], 1
        )

        self.assertEqual(
            Notification.objects.get().notification_type,
            Notification.Type.TASK_OVERDUE,
        )

    def test_future_task_not_yet_notified(self):
        self.create_task(hours_until_due=48)

        process_task_reminders()

        self.assertEqual(
            Notification.objects.count(), 0
        )

    def test_completed_task_not_notified(self):
        self.create_task(
            hours_until_due=1,
            status=SalesTask.Status.CANCELLED,
        )

        process_task_reminders()

        self.assertEqual(
            Notification.objects.count(), 0
        )

    def test_duplicate_reminders_prevented(self):
        self.create_task(hours_until_due=1)

        process_task_reminders()
        result = process_task_reminders()

        self.assertEqual(
            result["total_created"], 0
        )
        self.assertEqual(
            Notification.objects.count(), 1
        )

    def test_inactive_assignee_not_notified(self):
        self.create_task(hours_until_due=1)

        self.membership.is_active = False
        self.membership.save(
            update_fields=["is_active"]
        )

        process_task_reminders()

        self.assertEqual(
            Notification.objects.count(), 0
        )

    def test_owner_can_read_own_notifications(self):
        self.create_task(hours_until_due=1)
        process_task_reminders()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_unread_filter(self):
        self.create_task(hours_until_due=1)
        process_task_reminders()

        response = self.client.get(
            self.list_url,
            {"unread": "true"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_mark_notification_read(self):
        self.create_task(hours_until_due=1)
        process_task_reminders()

        notification = Notification.objects.get()

        read_url = reverse(
            "notification-mark-read",
            kwargs={
                "organization_id": self.org.id,
                "pk": notification.id,
            },
        )

        first = self.client.post(read_url)
        second = self.client.post(read_url)

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["changed"])

        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["changed"])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

        count_response = self.client.get(
            self.count_url
        )

        self.assertEqual(
            count_response.data["unread_count"], 0
        )

    def test_outsider_cannot_read_inbox(self):
        self.client.force_authenticate(
            user=self.outsider
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_read_inbox(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_inbox_is_recipient_scoped(self):
        other_user = User.objects.create_user(
            email="notification-colleague@example.com",
            password="SecureTest@2026!",
        )

        other_membership = Membership.objects.create(
            organization=self.org,
            user=other_user,
            role=Membership.Role.SALES_REP,
        )

        self.create_task(
            assigned_to=other_membership,
            hours_until_due=1,
        )

        process_task_reminders()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_cannot_mark_another_members_notification_read(self):
        other_user = User.objects.create_user(
            email="notification-other-rep@example.com",
            password="SecureTest@2026!",
        )

        other_membership = Membership.objects.create(
            organization=self.org,
            user=other_user,
            role=Membership.Role.SALES_REP,
        )

        self.create_task(
            assigned_to=other_membership,
            hours_until_due=1,
        )

        process_task_reminders()

        notification = Notification.objects.get()

        url = reverse(
            "notification-mark-read",
            kwargs={
                "organization_id": self.org.id,
                "pk": notification.id,
            },
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            Notification.objects.get().is_read
        )
    def test_due_soon_can_later_become_overdue(self):
        task = self.create_task(hours_until_due=1)

        first_now = timezone.now()
        first = process_task_reminders(now=first_now)

        second = process_task_reminders(
            now=task.due_at + timedelta(minutes=1)
        )

        self.assertEqual(first["due_soon_created"], 1)
        self.assertEqual(second["overdue_created"], 1)

        self.assertEqual(
            Notification.objects.filter(task=task).count(),
            2,
        )