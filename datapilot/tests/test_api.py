from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from datapilot.models import Dataset
from datapilot.models import Conversation, Turn

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

    @patch("datapilot.views.analyze")
    def test_analysis_persists_turn_attempt_and_returns_table(self, analyze):
        dataset = Dataset.objects.create(owner=self.user, original_filename="sales.csv", storage_path="private.csv",
                                         row_count=2, column_count=2,
                                         profile={"profile": [{"name": "region"}, {"name": "sales"}]})
        def run(*args, on_attempt, **kwargs):
            on_attempt({"attempt": 1, "code": "result = df", "status": "succeeded", "error": None})
            return {"status": "succeeded", "code": "result = df", "attempts": [], "error": None,
                    "result": {"kind": "table", "columns": ["region", "sales"], "rows": [["A", 10], ["B", 20]], "truncated": False}}
        analyze.side_effect = run
        response = self.client.post("/api/analysis/", {"dataset_id": str(dataset.pk), "question": "show sales"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        turn = Turn.objects.get()
        self.assertEqual(turn.attempts[0]["attempt"], 1)
        self.assertEqual(response.data["table"]["rows"], [["A", 10], ["B", 20]])
        self.assertEqual(Conversation.objects.get().owner, self.user)
        history = self.client.get(f"/api/conversations/{turn.conversation_id}/")
        self.assertEqual(len(history.data["turns"]), 1)

    def test_analysis_and_history_enforce_ownership(self):
        dataset = Dataset.objects.create(owner=self.other, original_filename="sales.csv", storage_path="private.csv",
                                         row_count=1, column_count=1, profile={"profile": []})
        response = self.client.post("/api/analysis/", {"dataset_id": str(dataset.pk), "question": "sum"}, format="json")
        self.assertEqual(response.status_code, 404)
        conversation = Conversation.objects.create(owner=self.other, dataset=dataset)
        self.assertEqual(self.client.get(f"/api/conversations/{conversation.pk}/").status_code, 404)
