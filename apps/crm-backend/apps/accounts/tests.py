from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticationAPITests(APITestCase):

    def test_registration(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "SecureTest@2026!",
                "confirm_password": "SecureTest@2026!",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            User.objects.filter(
                email="newuser@example.com"
            ).exists()
        )

    def test_password_is_hashed(self):
        self.client.post(
            reverse("register"),
            {
                "email": "hashed@example.com",
                "password": "SecureTest@2026!",
                "confirm_password": "SecureTest@2026!",
            },
        )

        user = User.objects.get(
            email="hashed@example.com"
        )

        self.assertNotEqual(
            user.password,
            "SecureTest@2026!"
        )

        self.assertTrue(
            user.check_password("SecureTest@2026!")
        )

    def test_profile_requires_authentication(self):
        response = self.client.get(
            reverse("current-user")
        )

        self.assertEqual(response.status_code, 401)