#!/usr/bin/env python3
import argparse
import json
import re
import sys

from tasktracker_api import TaskTrackerAPI
from tasktracker_url_utils import get_epic_id_from_url, get_project_id_from_url, get_task_id_from_url


ODATA_METHODS_REQUIRING_PROJECT_ID = {
    "odata_board",
    "odata_board_count",
    "odata_epic",
    "odata_epic_count",
    "odata_milestone",
    "odata_milestone_count",
    "odata_sprint",
    "odata_sprint_count",
    "odata_task",
    "odata_task_count",
    "odata_task_template_for_project",
    "odata_task_template_for_project_count",
    "odata_user_group_in_project_membership",
    "odata_user_group_in_project_membership_count",
    "odata_user_in_project_membership",
    "odata_user_in_project_membership_count",
}


HIDDEN_FILTER = "Hidden eq false"


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
        raise ValueError(
            "Named argument key is empty. In PowerShell wrap OData args in single quotes, "
            "for example: --odata-arg '$select=ID,Title' --odata-arg '$filter=Labels/any()'. "
            f"Received: {raw_arg}"
        )
    return key, parse_value(raw_value)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def has_exact_select_field(select_value, field_name):
    if not isinstance(select_value, str):
        return False
    select_fields = [part.strip() for part in select_value.split(",")]
    return field_name in select_fields


def has_exact_orderby_field(orderby_value, field_name):
    if not isinstance(orderby_value, str):
        return False
    orderby_fields = []
    for part in orderby_value.split(","):
        tokens = part.strip().split()
        if tokens:
            orderby_fields.append(tokens[0])
    return field_name in orderby_fields


def contains_filter_field_in_lowercase(filter_value, field_name):
    if not isinstance(filter_value, str):
        return False
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(field_name)}(?![A-Za-z0-9_])", filter_value) is not None


def apply_default_hidden_filter(python_method, odata_args, include_hidden=False):
    if include_hidden or not python_method.startswith("odata_"):
        return dict(odata_args)

    normalized_args = dict(odata_args)
    raw_filter = normalized_args.get("$filter")
    if raw_filter is None:
        normalized_args["$filter"] = HIDDEN_FILTER
        return normalized_args

    if not isinstance(raw_filter, str):
        raise ValueError("$filter must be a string when passed through --odata-arg.")

    stripped_filter = raw_filter.strip()
    if not stripped_filter:
        normalized_args["$filter"] = HIDDEN_FILTER
        return normalized_args

    if stripped_filter == HIDDEN_FILTER:
        normalized_args["$filter"] = HIDDEN_FILTER
        return normalized_args

    normalized_args["$filter"] = f"({stripped_filter}) and {HIDDEN_FILTER}"
    return normalized_args


def validate_odata_usage(python_method, keyword_args, odata_args):
    if not python_method.startswith("odata_"):
        return

    if python_method in ODATA_METHODS_REQUIRING_PROJECT_ID and "project_id" not in keyword_args:
        raise ValueError(
            f"{python_method} requires --arg project_id=<value>. "
            "The API returns HTTP 400 without projectId for this endpoint."
        )

    should_print_pascal_case_hint = False

    if "$select" in odata_args and isinstance(odata_args["$select"], str):
        select_value = odata_args["$select"]
        if any(has_exact_select_field(select_value, field_name) for field_name in ("id", "title", "labels")):
            should_print_pascal_case_hint = True
            print(
                "[tasktracker-api] Hint: prefer $select=ID,Title,Labels instead of camelCase names.",
                file=sys.stderr,
            )

    if "$orderby" in odata_args and isinstance(odata_args["$orderby"], str):
        orderby_value = odata_args["$orderby"]
        if any(has_exact_orderby_field(orderby_value, field_name) for field_name in ("id", "title", "labels")):
            should_print_pascal_case_hint = True

    if "$filter" in odata_args and isinstance(odata_args["$filter"], str):
        filter_value = odata_args["$filter"]
        if (
            contains_filter_field_in_lowercase(filter_value, "labels")
            or contains_filter_field_in_lowercase(filter_value, "title")
            or contains_filter_field_in_lowercase(filter_value, "id")
        ):
            should_print_pascal_case_hint = True
            print(
                "[tasktracker-api] Hint: for label filters use PascalCase field names, "
                "for example Labels/any(l:l/Title eq 'Тестирование') or Labels/any(l:l/ID eq 80).",
                file=sys.stderr,
            )
        if "Labels" in filter_value and "$expand" not in odata_args:
            print(
                "[tasktracker-api] Hint: add --odata-arg '$expand=Labels' if you need label objects in the response body.",
                file=sys.stderr,
            )

    if should_print_pascal_case_hint:
        hint = (
            "OData field names on the wire usually use PascalCase, for example ID, Title, Labels, "
            "even if the local index shows camelCase names."
        )
        print(f"[tasktracker-api] Hint: {hint}", file=sys.stderr)


def main():
    configure_stdout()
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
    parser.add_argument(
        "--odata-arg",
        action="append",
        default=[],
        help="OData query argument in key=value form, for example $filter=Status eq 'Open'",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Allow reading hidden entities in OData endpoints without the default Hidden eq false filter",
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
    odata_args = dict(parse_named_arg(value) for value in args.odata_arg)
    odata_args = apply_default_hidden_filter(
        python_method,
        odata_args,
        include_hidden=args.include_hidden,
    )
    validate_odata_usage(python_method, keyword_args, odata_args)

    api = TaskTrackerAPI()
    result = api.call_by_python_method(
        python_method,
        *positional_args,
        odata_params=odata_args,
        **keyword_args,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
