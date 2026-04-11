import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "calendar-api" / "scripts" / "calendar_call.py"


def load_calendar_call_module():
    fake_api_module = types.ModuleType("calendar_api")
    fake_api_module.CalendarAPI = object
    sys.modules["calendar_api"] = fake_api_module

    spec = importlib.util.spec_from_file_location("calendar_call_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NormalizeKeywordArgsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_calendar_call_module()

    def test_import_requires_file(self):
        with self.assertRaises(ValueError):
            self.module.normalize_keyword_args("post_calendar_import_id", {}, None)

    def test_import_adds_file_path(self):
        result = self.module.normalize_keyword_args("post_calendar_import_id", {}, "sample.ics")
        self.assertEqual({"file_path": "sample.ics"}, result)

    def test_body_must_be_object(self):
        with self.assertRaises(ValueError):
            self.module.normalize_keyword_args("post_event", {"body": ["bad"]}, None)

    def test_file_is_rejected_for_non_import_methods(self):
        with self.assertRaises(ValueError):
            self.module.normalize_keyword_args("get_calendar", {}, "sample.ics")

    def test_event_body_normalizes_calendar_id_and_user_ids(self):
        result = self.module.normalize_keyword_args(
            "post_event",
            {
                "body": {
                    "calendarId": 12,
                    "title": "Demo",
                    "users": [1, 3, 4, 5],
                }
            },
            None,
        )
        self.assertEqual({"ID": 12}, result["body"]["Calendar"])
        self.assertEqual(
            [{"UserId": 1}, {"UserId": 3}, {"UserId": 4}, {"UserId": 5}],
            result["body"]["Users"],
        )
        self.assertEqual("Demo", result["body"]["Title"])
        self.assertNotIn("calendarId", result["body"])
        self.assertNotIn("users", result["body"])

    def test_event_body_normalizes_nested_user_and_group_objects(self):
        result = self.module.normalize_keyword_args(
            "patch_event",
            {
                "body": {
                    "Calendar": {"id": 12},
                    "Users": [{"ID": 1}, {"UserId": 3}],
                    "Groups": [7, {"Id": 9}],
                    "Notifications": [15, {"minutes": 30}],
                }
            },
            None,
        )
        self.assertEqual({"ID": 12}, result["body"]["Calendar"])
        self.assertEqual([{"UserId": 1}, {"UserId": 3}], result["body"]["Users"])
        self.assertEqual([{"GroupId": 7}, {"GroupId": 9}], result["body"]["Groups"])
        self.assertEqual(
            [{"NotificationTime": 15}, {"NotificationTime": 30}],
            result["body"]["Notifications"],
        )

    def test_event_body_rejects_invalid_users_shape(self):
        with self.assertRaises(ValueError):
            self.module.normalize_keyword_args(
                "post_event",
                {"body": {"Calendar": {"ID": 12}, "Users": [{"name": "bad"}]}},
                None,
            )


class WriteExportResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_calendar_call_module()

    def test_write_export_response_saves_file_and_returns_metadata(self):
        class Response:
            status_code = 200
            headers = {"Content-Type": "text/calendar", "Content-Disposition": 'attachment; filename="team.ics"'}
            content = b"BEGIN:VCALENDAR\nEND:VCALENDAR\n"

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "team.ics"
            result = self.module.write_export_response(Response(), output_path=output_path)
            self.assertEqual(Response.content, output_path.read_bytes())
            self.assertEqual(str(output_path.resolve()), result["outputPath"])
            self.assertEqual("text/calendar", result["contentType"])
            self.assertIn("VCALENDAR", result["text"])


if __name__ == "__main__":
    unittest.main()
