import importlib.util
import io
import sys
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "tasktracker-api" / "scripts" / "tasktracker_call.py"


def load_tasktracker_call_module():
    fake_api_module = types.ModuleType("tasktracker_api")
    fake_api_module.TaskTrackerAPI = object
    sys.modules["tasktracker_api"] = fake_api_module

    fake_url_utils_module = types.ModuleType("tasktracker_url_utils")
    fake_url_utils_module.get_epic_id_from_url = lambda value: value
    fake_url_utils_module.get_project_id_from_url = lambda value: value
    fake_url_utils_module.get_task_id_from_url = lambda value: value
    sys.modules["tasktracker_url_utils"] = fake_url_utils_module

    spec = importlib.util.spec_from_file_location("tasktracker_call_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ApplyDefaultHiddenFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_tasktracker_call_module()

    def test_non_odata_method_is_unchanged(self):
        result = self.module.apply_default_hidden_filter("get_task_query_get_task_id", {}, include_hidden=False)
        self.assertEqual({}, result)

    def test_odata_method_adds_default_hidden_filter(self):
        result = self.module.apply_default_hidden_filter("odata_task", {}, include_hidden=False)
        self.assertEqual({"$filter": "Hidden eq false"}, result)

    def test_existing_filter_is_combined_with_hidden_filter(self):
        result = self.module.apply_default_hidden_filter(
            "odata_task",
            {"$filter": "State eq 10", "$top": 50},
            include_hidden=False,
        )
        self.assertEqual({"$filter": "(State eq 10) and Hidden eq false", "$top": 50}, result)

    def test_blank_filter_is_replaced_with_default_hidden_filter(self):
        result = self.module.apply_default_hidden_filter("odata_task", {"$filter": "   "}, include_hidden=False)
        self.assertEqual({"$filter": "Hidden eq false"}, result)

    def test_include_hidden_keeps_original_filter(self):
        result = self.module.apply_default_hidden_filter(
            "odata_task",
            {"$filter": "Hidden eq true"},
            include_hidden=True,
        )
        self.assertEqual({"$filter": "Hidden eq true"}, result)

    def test_existing_safe_hidden_filter_is_not_wrapped_twice(self):
        result = self.module.apply_default_hidden_filter(
            "odata_task_count",
            {"$filter": "Hidden eq false"},
            include_hidden=False,
        )
        self.assertEqual({"$filter": "Hidden eq false"}, result)

    def test_non_string_filter_raises(self):
        with self.assertRaises(ValueError):
            self.module.apply_default_hidden_filter("odata_task", {"$filter": True}, include_hidden=False)


class ValidateODataUsageHintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_tasktracker_call_module()

    def capture_stderr(self, python_method, keyword_args, odata_args):
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            self.module.validate_odata_usage(python_method, keyword_args, odata_args)
        return buffer.getvalue()

    def test_hidden_field_does_not_trigger_camelcase_hints(self):
        stderr_output = self.capture_stderr(
            "odata_epic",
            {"project_id": 12},
            {"$select": "ID,Title,Hidden", "$filter": "Hidden eq false"},
        )
        self.assertEqual("", stderr_output)
        self.assertNotIn("prefer $select=ID,Title,Labels", stderr_output)
        self.assertNotIn("for label filters use PascalCase", stderr_output)

    def test_lowercase_select_fields_trigger_hint(self):
        stderr_output = self.capture_stderr(
            "odata_epic",
            {"project_id": 12},
            {"$select": "id,title,Hidden", "$filter": "Hidden eq false"},
        )
        self.assertIn("PascalCase", stderr_output)
        self.assertIn("prefer $select=ID,Title,Labels", stderr_output)

    def test_lowercase_filter_fields_trigger_hint(self):
        stderr_output = self.capture_stderr(
            "odata_epic",
            {"project_id": 12},
            {"$filter": "labels/any(l:l/title eq 'x')"},
        )
        self.assertIn("PascalCase", stderr_output)
        self.assertIn("for label filters use PascalCase", stderr_output)


if __name__ == "__main__":
    unittest.main()
