from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from datapilot.models import Dataset
from datapilot.services.rag import build_schema_context, index_dataset
from datapilot.services.analysis import analyze


class SchemaRagTests(SimpleTestCase):
    def _dataset(self, column_count=40):
        columns = [
            {"name": f"field_{number}", "type": "object", "missing_count": 0,
             "distinct_count": 10, "samples": [f"sample {number}"]}
            for number in range(column_count)
        ]
        return Dataset(
            column_count=column_count, row_count=100,
            profile={"rows": 100, "columns": column_count, "profile": columns},
        )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("google.genai.Client")
    def test_gemini_embedding_sdk_uses_configured_model_task_and_dimension(self, client_class):
        from datapilot.services.rag import embed_text

        client = client_class.return_value
        client.models.embed_content.return_value.embeddings = [
            SimpleNamespace(values=[0.25] * 768)
        ]

        vector = embed_text("Column: revenue", task_type="RETRIEVAL_DOCUMENT")

        request = client.models.embed_content.call_args.kwargs
        self.assertEqual(request["model"], "gemini-embedding-001")
        self.assertEqual(request["config"].task_type, "RETRIEVAL_DOCUMENT")
        self.assertEqual(request["config"].output_dimensionality, 768)
        self.assertEqual(len(vector), 768)

    @patch("datapilot.services.rag.embed_text", return_value=[0.1] * 768)
    @patch("datapilot.services.rag.ColumnSchema.objects")
    def test_indexing_embeds_bounded_privacy_filtered_column_metadata(self, manager, embed):
        manager.filter.side_effect = [[], MagicMock()]
        dataset = Dataset(
            row_count=2,
            profile={"rows": 2, "columns": 1, "profile": [
                {"name": "email", "type": "object", "missing_count": 0,
                 "distinct_count": 1, "samples": ["private@example.com"]}
            ]},
        )

        self.assertEqual(index_dataset(dataset), 1)

        saved = manager.bulk_create.call_args.args[0][0]
        self.assertNotIn("private@example.com", saved.searchable_text)
        embed.assert_called_once()
        self.assertNotIn("private@example.com", embed.call_args.args[0])
        self.assertEqual(len(embed.return_value), 768)

    @override_settings(DATASET_RAG_COLUMN_THRESHOLD=3, ANALYSIS_RAG_TOP_K=2)
    @patch("datapilot.services.rag.embed_text", return_value=[0.2] * 768)
    @patch("datapilot.services.rag.ColumnSchema.objects")
    def test_retrieval_is_dataset_scoped_and_selects_top_k_columns(self, manager, embed):
        query = MagicMock()
        manager.filter.return_value = query
        ordered = query.annotate.return_value.order_by
        ordered.return_value.__getitem__.return_value = [
            SimpleNamespace(column_name="field_7", data_type="integer",
                            searchable_text="Column: field_7", distance=0.12)
        ]

        dataset = self._dataset()
        context = build_schema_context(dataset, "sum revenue")

        manager.filter.assert_called_once_with(dataset=dataset, embedding__isnull=False)
        self.assertEqual(query.annotate.call_count, 1)
        self.assertEqual(ordered.call_args.args, ("distance",))
        self.assertEqual(ordered.return_value.__getitem__.call_args.args[0], slice(None, 2, None))
        self.assertIn('"name": "field_7"', context)
        self.assertNotIn('"name": "field_0"', context)
        embed.assert_called_once()

    @override_settings(DATASET_RAG_COLUMN_THRESHOLD=3)
    @patch("datapilot.services.rag.embed_text", side_effect=RuntimeError("network details"))
    def test_embedding_failure_falls_back_to_full_profile_without_leaking_error(self, embed):
        context = build_schema_context(self._dataset(), "question")
        self.assertIn('"name": "field_0"', context)
        self.assertIn('"name": "field_39"', context)

    @override_settings(DATASET_RAG_COLUMN_THRESHOLD=40)
    @patch("datapilot.services.rag.embed_text")
    def test_small_dataset_uses_full_profile_without_embeddings(self, embed):
        context = build_schema_context(self._dataset(), "question")
        self.assertIn('"name": "field_0"', context)
        embed.assert_not_called()

    @override_settings(DATASET_RAG_COLUMN_THRESHOLD=3, ANALYSIS_RAG_MAX_COSINE_DISTANCE=0.2)
    @patch("datapilot.services.rag.embed_text", return_value=[0.2] * 768)
    @patch("datapilot.services.rag.ColumnSchema.objects")
    def test_no_useful_matches_falls_back_to_full_profile(self, manager, embed):
        query = MagicMock()
        manager.filter.return_value = query
        query.annotate.return_value.order_by.return_value.__getitem__.return_value = [
            SimpleNamespace(column_name="field_1", data_type="text",
                            searchable_text="Column: field_1", distance=0.8)
        ]
        context = build_schema_context(self._dataset(), "question")
        self.assertIn('"name": "field_0"', context)

    @patch("datapilot.services.analysis.execute", return_value={"kind": "scalar", "value": 5})
    @patch("datapilot.services.analysis.generate_code", return_value="result = 5")
    @patch("datapilot.services.rag.build_schema_context", return_value='{"profile":[{"name":"field_7"}]}')
    def test_retrieved_schema_is_passed_to_gemini_code_generation(self, schema_context, generate, execute):
        result = analyze("question", "ignored full schema", "dataset.csv", dataset=self._dataset())
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(generate.call_args.args[1], '{"profile":[{"name":"field_7"}]}')
