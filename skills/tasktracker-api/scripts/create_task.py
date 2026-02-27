#!/usr/bin/env python3
import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_base_url,
    get_first_present_value,
    get_token,
    http_post_json,
    load_env_from_dotenv,
    print_execution_error,
    print_http_error,
    print_network_error,
)


def parse_csv_ints(raw: Optional[str], arg_name: str) -> List[int]:
    if not raw:
        return []

    values: List[int] = []
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        if not value.isdigit():
            raise ValueError(f"{arg_name} must contain integers separated by commas")
        values.append(int(value))

    return values


def get_project_id(cli_value: Optional[int]) -> int:
    if cli_value is not None:
        return cli_value

    env_value = (
        os.getenv("erp_tasktracker_project_id")
        or os.getenv("erp-tasktracker-project-id")
        or os.getenv("project-id")
        or os.getenv("projectId")
    )
    if env_value is None:
        raise ValueError(
            "projectId is required: pass --project-id or set erp_tasktracker_project_id in .env"
        )

    env_value = env_value.strip()
    if not env_value.isdigit():
        raise ValueError("erp_tasktracker_project_id in .env must be an integer")
    return int(env_value)


def require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required and cannot be empty")
    return cleaned


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    title = require_non_empty(args.title, "Title")
    description = require_non_empty(args.description, "Description")
    project_id = get_project_id(args.project_id)

    payload: Dict[str, Any] = {
        "LabelIds": parse_csv_ints(args.label_ids, "label-ids"),
        "AssigneeIds": [],
        "CurrentAssigneeId": None,
        "Weight": args.weight,
        "Description": description,
        "Files": "",
        "SprintId": args.sprint_id,
        "MilestoneId": args.milestone_id,
        "TemplateId": None,
        "Title": title,
        "EpicId": args.epic_id,
        "projectId": project_id,
    }

    return payload


def create_task(base_url: str, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    create_url = f"{base_url.rstrip('/')}/api/tasktracker/task/command/create"
    return http_post_json(create_url, token, payload, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create TaskTracker task using ERP client credentials token"
    )
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--description", required=True, help="Task description")
    parser.add_argument(
        "--project-id",
        type=int,
        help="Project ID (fallback: .env erp_tasktracker_project_id)",
    )
    parser.add_argument("--epic-id", type=int, help="Epic ID")
    parser.add_argument("--label-ids", help="Comma-separated label IDs, e.g. 6,73")
    parser.add_argument("--weight", type=int, help="Task weight")
    parser.add_argument("--sprint-id", type=int, help="Sprint ID")
    parser.add_argument("--milestone-id", type=int, help="Milestone ID")
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        payload = build_payload(args)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = create_task(base_url, token, payload, args.timeout)

        if isinstance(response, dict):
            task_id = get_first_present_value(response, ("TaskId", "taskId", "Id", "id"))
            title = get_first_present_value(response, ("Title", "title")) or payload["Title"]
            description = (
                get_first_present_value(response, ("Description", "description"))
                or payload["Description"]
            )
            project_id = get_first_present_value(response, ("projectId", "ProjectId")) or payload["projectId"]
        else:
            task_id = None
            title = payload["Title"]
            description = payload["Description"]
            project_id = payload["projectId"]

        result = {
            "TaskId": task_id,
            "Title": title,
            "Description": description,
            "projectId": project_id,
            "baseUrl": base_url,
            "apiResponse": response,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except HTTPError as exc:
        print_http_error(exc)
        return 1
    except URLError as exc:
        print_network_error(exc)
        return 1
    except Exception as exc:
        print_execution_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

