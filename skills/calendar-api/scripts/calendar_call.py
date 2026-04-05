#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from calendar_api import CalendarAPI


BODY_METHODS = {
    "post_calendar",
    "patch_calendar_id",
    "post_event",
    "patch_event",
    "post_permission",
    "patch_permission",
}
IMPORT_METHODS = {"post_calendar_import_id"}
EXPORT_METHODS = {"get_calendar_export_id"}


def parse_value(raw_value):
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def parse_named_arg(raw_arg):
    if "=" not in raw_arg:
        raise ValueError(f"Named argument must be key=value: {raw_arg}")
    key, raw_value = raw_arg.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Named argument key is empty: {raw_arg}")
    return key, parse_value(raw_value)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def normalize_keyword_args(python_method, keyword_args, file_path):
    normalized_args = dict(keyword_args)
    if python_method in IMPORT_METHODS:
        if not file_path:
            raise ValueError(f"{python_method} requires --file <path>.")
        normalized_args["file_path"] = file_path
    elif file_path:
        raise ValueError("--file is supported only for calendar import endpoints.")

    if python_method in BODY_METHODS and "body" in normalized_args and normalized_args["body"] is not None:
        if not isinstance(normalized_args["body"], dict):
            raise ValueError("--arg body must be a JSON object.")
    return normalized_args


def write_export_response(response, output_path=None):
    content = response.content
    if output_path:
        destination = Path(output_path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = None

    return {
        "statusCode": response.status_code,
        "contentType": response.headers.get("Content-Type"),
        "contentDisposition": response.headers.get("Content-Disposition"),
        "size": len(content),
        "outputPath": str(Path(output_path).expanduser().resolve()) if output_path else None,
        "text": text,
    }


def main():
    configure_stdout()
    parser = argparse.ArgumentParser(description="Call CalendarAPI method by method name")
    parser.add_argument("-m", "--python-method", required=True, help="Python method name from assets/calendar.json")
    parser.add_argument("--posarg", action="append", default=[], help="Positional argument value; parsed as JSON when possible")
    parser.add_argument("--arg", action="append", default=[], help="Named argument in key=value form; value is parsed as JSON when possible")
    parser.add_argument("--file", help="File path for multipart upload endpoints")
    parser.add_argument("--output", help="Write export response content to this path")
    args = parser.parse_args()

    positional_args = [parse_value(value) for value in args.posarg]
    keyword_args = dict(parse_named_arg(value) for value in args.arg)
    keyword_args = normalize_keyword_args(args.python_method, keyword_args, args.file)

    if args.output and args.python_method not in EXPORT_METHODS:
        raise ValueError("--output is supported only for calendar export endpoints.")

    api = CalendarAPI()
    result = api.call_by_python_method(args.python_method, *positional_args, **keyword_args)
    if args.python_method in EXPORT_METHODS:
        result = write_export_response(result, output_path=args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
