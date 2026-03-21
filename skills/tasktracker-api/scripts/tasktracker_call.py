#!/usr/bin/env python3
import argparse
import json

from tasktracker_api import TaskTrackerAPI
from tasktracker_url_utils import get_epic_id_from_url, get_project_id_from_url, get_task_id_from_url


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


def main():
    parser = argparse.ArgumentParser(
        description="Call TaskTrackerAPI method by method name"
    )
    parser.add_argument("-m", "--python-method", required=True, help="Python method name from assets/method_index.json")
    parser.add_argument(
        "--posarg",
        action="append",
        default=[],
        help="Positional argument value; parsed as JSON when possible",
    )
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Named argument in key=value form; value is parsed as JSON when possible",
    )
    parser.add_argument("--task-url", help="Extract taskId from URL and prepend it to positional arguments")
    parser.add_argument("--epic-url", help="Extract epicId from URL and prepend it to positional arguments")
    parser.add_argument("--project-url", help="Extract projectId from URL and prepend it to positional arguments")
    args = parser.parse_args()
    python_method = args.python_method

    positional_args = [parse_value(value) for value in args.posarg]
    derived_positional_args = []
    if args.task_url:
        derived_positional_args.append(get_task_id_from_url(args.task_url))
    if args.epic_url:
        derived_positional_args.append(get_epic_id_from_url(args.epic_url))
    if args.project_url:
        derived_positional_args.append(get_project_id_from_url(args.project_url))
    positional_args = derived_positional_args + positional_args
    keyword_args = dict(parse_named_arg(value) for value in args.arg)

    api = TaskTrackerAPI()
    method = getattr(api, python_method, None)
    if method is None:
        raise AttributeError(f"TaskTrackerAPI has no method {python_method}")

    result = method(*positional_args, **keyword_args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
