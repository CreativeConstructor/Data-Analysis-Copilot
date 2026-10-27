from django.test import SimpleTestCase
from datapilot.services.validator import validate

class ValidatorTests(SimpleTestCase):
    def test_allows_pandas_analysis_and_result(self):
        self.assertEqual(validate("import pandas as pd\nresult = df['sales'].sum()"), [])

    def test_rejects_file_access_and_unlisted_imports(self):
        errors = validate("import os\nresult = df")
        self.assertTrue(any(error["rule"] == "imports" for error in errors))

    def test_rejects_read_methods_even_through_dataframe(self):
        errors = validate("result = pd.read_csv('x.csv')")
        self.assertTrue(any(error["rule"] == "file_io" for error in errors))

    def test_rejects_file_reader_alias_before_it_can_be_called(self):
        errors = validate("reader = pd.read_csv\nresult = reader('x.csv')")
        self.assertTrue(any(error["rule"] == "file_io" for error in errors))

    def test_rejects_imported_file_reader_alias(self):
        errors = validate("from pandas.io.parsers import read_csv as load\nresult = load('x.csv')")
        self.assertTrue(any(error["rule"] == "imports" for error in errors))

    def test_requires_result(self):
        self.assertIn("result", [error["rule"] for error in validate("print(df.head())")])

    def test_checks_literal_dataframe_columns_when_schema_is_available(self):
        errors = validate("result = df['missing'].sum()", columns=["sales"])
        self.assertIn("missing_column", [error["rule"] for error in errors])

    def test_allows_valid_literal_dataframe_column(self):
        self.assertEqual(validate("result = df['sales'].sum()", columns=["sales"]), [])

    def test_rejects_dunder_attribute(self):
        self.assertIn("dunder_attribute", [error["rule"] for error in validate("result = df.__class__")])
