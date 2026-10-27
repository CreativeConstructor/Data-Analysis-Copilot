from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from datapilot.models import Dataset

class DatasetApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="pw")
        self.other = get_user_model().objects.create_user(username="other", password="pw")
        self.client.force_authenticate(self.user)

    @patch.dict("os.environ", {}, clear=True)
    def test_upload_list_detail_and_delete_owned_dataset(self):
        uploaded = SimpleUploadedFile("sales.csv", b"region,revenue\nNorth,100\nSouth,150\n", content_type="text/csv")
        response = self.client.post("/api/datasets/", {"file": uploaded}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        dataset_id = response.data["id"]
        self.assertEqual(response.data["row_count"], 2)
        self.assertEqual(self.client.get("/api/datasets/").data[0]["id"], dataset_id)
        self.assertEqual(self.client.get(f"/api/datasets/{dataset_id}/").status_code, 200)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/datasets/{dataset_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/datasets/{dataset_id}/").status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f"/api/datasets/{dataset_id}/").status_code, 204)
        self.assertFalse(Dataset.objects.filter(pk=dataset_id).exists())

    def test_rejects_unsupported_extension(self):
        uploaded = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = self.client.post("/api/datasets/", {"file": uploaded}, format="multipart")
        self.assertEqual(response.status_code, 400)
