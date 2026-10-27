from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase, override_settings
from datapilot.services.datasets import make_profile, read_dataset

class DatasetProfileTests(SimpleTestCase):
    def test_profiles_csv_rows_types_missing_values_and_numeric_stats(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "example.csv"
            path.write_text("region,revenue\nNorth,100\nSouth,\nNorth,300\n", encoding="utf-8")
            frame = read_dataset(path)
        profile = make_profile(frame)
        self.assertEqual(profile["rows"], 3)
        self.assertEqual(profile["columns"], 2)
        revenue = profile["profile"][1]
        self.assertEqual(revenue["missing_count"], 1)
        self.assertEqual(revenue["distinct_count"], 2)
        self.assertEqual(revenue["statistics"]["mean"], 200.0)
        self.assertLessEqual(len(revenue["samples"]), 5)

    @override_settings(DATASET_MAX_ROWS=1)
    def test_rejects_csv_above_configured_row_limit(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "too-many.csv"
            path.write_text("amount\n1\n2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "row limit"):
                read_dataset(path)

    @override_settings(DATASET_MAX_COLUMNS=1)
    def test_rejects_csv_above_configured_column_limit(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "too-wide.csv"
            path.write_text("a,b\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "column limit"):
                read_dataset(path)

    def test_returns_clear_error_for_malformed_csv(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text('a,b\n"unterminated,1\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed"):
                read_dataset(path)
