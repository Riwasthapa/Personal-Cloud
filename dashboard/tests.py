from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


class DashboardStorageTests(TestCase):
    def setUp(self):
        self.storage_dir = TemporaryDirectory()
        self.settings_override = override_settings(
            ANDROID_MEDIA_ROOT=self.storage_dir.name
        )
        self.settings_override.enable()
        user = get_user_model().objects.create_user(
            email="storage@example.com",
            password="test-password",
        )
        self.client.force_login(user)

    def tearDown(self):
        self.settings_override.disable()
        self.storage_dir.cleanup()

    def test_sidebar_shows_available_space_on_storage_volume(self):
        expected_free_bytes = 25 * 1024**3
        expected_used_percent = 75

        with patch(
            "dashboard.views.shutil.disk_usage",
            return_value=SimpleNamespace(
                free=expected_free_bytes,
                used=75 * 1024**3,
                total=100 * 1024**3,
            ),
        ) as disk_usage:
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["available_storage_bytes"],
            expected_free_bytes,
        )
        self.assertEqual(
            response.context["storage_used_percent"],
            expected_used_percent,
        )
        self.assertContains(response, "Available storage")
        self.assertContains(
            response,
            'aria-valuenow="75"',
        )
        self.assertContains(response, "75% used on this device")
        disk_usage.assert_called_once_with(self.storage_dir.name)

    def test_sidebar_storage_percentage_is_zero_for_empty_volume(self):
        with patch(
            "dashboard.views.shutil.disk_usage",
            return_value=SimpleNamespace(free=0, used=0, total=0),
        ):
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["storage_used_percent"], 0)

    def test_folders_page_opens_from_sidebar_destination(self):
        response = self.client.get(reverse("folders"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h2>Folders</h2>")
        self.assertContains(response, 'href="/folders/" class="nav-link active"')
