
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.organizations.models import Organization, Membership
from apps.leads.models import Lead
from apps.tasks.models import SalesTask

from apps.ai_assistant.tools.executor import (
    authorize_tool_context,
    execute_read_only_tool,
)


User = get_user_model()


class TaskToolTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="task-tool-owner@example.com",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="task-tool-other@example.com",
            password="TestPassword123!",
        )

        cls.org = Organization.objects.create(
            name="Task Tool Organization",
            slug="task-tool-org",
            created_by=cls.owner,
        )

        cls.owner_membership = Membership.objects.create(
            organization=cls.org,
            user=cls.owner,
            role=Membership.Role.OWNER,
            is_active=True,
        )

        cls.other_membership = Membership.objects.create(
            organization=cls.org,
            user=cls.other_user,
            role=Membership.Role.SALES_REP,
            is_active=True,
        )

        cls.lead = Lead.objects.create(
            organization=cls.org,
            title="Test Customer Lead",
            created_by=cls.owner,
            status=Lead.Status.NEW,
        )

        cls.overdue_task = SalesTask.objects.create(
            organization=cls.org,
            title="Call overdue customer",
            assigned_to=cls.owner_membership,
            created_by=cls.owner,
            lead=cls.lead,
            priority=SalesTask.Priority.HIGH,
            status=SalesTask.Status.PENDING,
            due_at=timezone.now() - timedelta(days=2),
        )

        cls.upcoming_task = SalesTask.objects.create(
            organization=cls.org,
            title="Prepare follow-up proposal",
            assigned_to=cls.owner_membership,
            created_by=cls.owner,
            lead=cls.lead,
            priority=SalesTask.Priority.MEDIUM,
            status=SalesTask.Status.PENDING,
            due_at=timezone.now() + timedelta(days=2),
        )

        cls.other_task = SalesTask.objects.create(
            organization=cls.org,
            title="Other employee private task",
            assigned_to=cls.other_membership,
            created_by=cls.owner,
            lead=cls.lead,
            priority=SalesTask.Priority.LOW,
            status=SalesTask.Status.PENDING,
            due_at=timezone.now() - timedelta(days=1),
        )

    def setUp(self):
        self.context = authorize_tool_context(
            user=self.owner,
            organization_id=self.org.id,
        )

    def run_tool(self, arguments):
        return execute_read_only_tool(
            tool_name="list_my_tasks",
            arguments=arguments,
            context=self.context,
        )

    def test_lists_own_pending_tasks(self):
        result = self.run_tool({})

        titles = [task["title"] for task in result["tasks"]]

        self.assertEqual(result["returned_count"], 2)
        self.assertIn("Call overdue customer", titles)
        self.assertIn("Prepare follow-up proposal", titles)

    def test_excludes_other_employee_tasks(self):
        result = self.run_tool({})

        titles = [task["title"] for task in result["tasks"]]

        self.assertNotIn(
            "Other employee private task",
            titles,
        )

    def test_overdue_only(self):
        result = self.run_tool({
            "overdue_only": True,
        })

        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(
            result["tasks"][0]["title"],
            "Call overdue customer",
        )
        self.assertTrue(result["tasks"][0]["is_overdue"])

    def test_limit(self):
        result = self.run_tool({
            "limit": 1,
        })

        self.assertEqual(result["returned_count"], 1)

    def test_invalid_limit(self):
        result = self.run_tool({
            "limit": 100,
        })

        self.assertEqual(
            result["error"],
            "invalid_limit",
        )

    def test_rejects_user_override(self):
        from apps.ai_assistant.tools.executor import (
            ToolExecutionError,
        )

        with self.assertRaises(ToolExecutionError):
            self.run_tool({
                "user_id": str(self.other_user.pk),
            })

    def test_does_not_modify_tasks(self):
        original_status = self.overdue_task.status

        self.run_tool({
            "overdue_only": True,
        })

        self.overdue_task.refresh_from_db()

        self.assertEqual(
            self.overdue_task.status,
            original_status,
        )
