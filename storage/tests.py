from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse


class FileUploadTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.settings_override = override_settings(
            ANDROID_MEDIA_ROOT=Path(self.media_dir.name)
        )
        self.settings_override.enable()
        self.user = get_user_model().objects.create_user(
            email="uploader@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.upload_url = reverse("upload_file")

    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    def test_upload_form_accepts_multiple_files(self):
        response = self.client.get(self.upload_url)

        self.assertContains(response, 'name="files"')
        self.assertContains(response, "multiple")
        self.assertContains(response, 'href="/storage/upload/" class="nav-link active"')
        self.assertContains(response, "Available storage")
        self.assertContains(response, "About Personal Cloud")
        self.assertContains(response, "Choose files to upload")

    def test_dashboard_loads_for_signed_in_user(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

    def test_uploads_multiple_files(self):
        response = self.client.post(
            self.upload_url,
            {
                "files": [
                    SimpleUploadedFile("first.txt", b"first file"),
                    SimpleUploadedFile("second.txt", b"second file"),
                ]
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(
            (Path(self.media_dir.name) / "first.txt").read_bytes(),
            b"first file",
        )
        self.assertEqual(
            (Path(self.media_dir.name) / "second.txt").read_bytes(),
            b"second file",
        )

    def test_requires_at_least_one_file(self):
        response = self.client.post(self.upload_url, {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")

    def test_rejects_batch_when_a_file_name_already_exists(self):
        (Path(self.media_dir.name) / "existing.txt").write_bytes(b"existing")

        response = self.client.post(
            self.upload_url,
            {
                "files": [
                    SimpleUploadedFile("new.txt", b"new file"),
                    SimpleUploadedFile("existing.txt", b"replacement"),
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A file with that name already exists.")
        self.assertFalse((Path(self.media_dir.name) / "new.txt").exists())
        self.assertEqual(
            (Path(self.media_dir.name) / "existing.txt").read_bytes(),
            b"existing",
        )

    def test_rejects_duplicate_names_within_batch(self):
        response = self.client.post(
            self.upload_url,
            {
                "files": [
                    SimpleUploadedFile("same.txt", b"first"),
                    SimpleUploadedFile("same.txt", b"second"),
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A file with that name already exists.")
        self.assertFalse((Path(self.media_dir.name) / "same.txt").exists())
