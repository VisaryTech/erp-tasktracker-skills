#!/usr/bin/env python3
import argparse
import json
import re
from typing import Any, Dict, Literal, Tuple
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_base_url,
    get_first_present_value,
    get_token,
    http_get_json,
    load_env_from_dotenv,
    print_execution_error,
    print_http_error,
    print_network_error,
)


def parse_url_entity(tasktracker_url: str) -> Tuple[Literal["task", "epic"], str]:
    match = re.search(r"/tasks/([0-9]+)", tasktracker_url)
    if match:
        return "task", match.group(1)

    match = re.search(r"/epics/([0-9]+)", tasktracker_url)
    if not match:
        raise ValueError("Cannot extract TaskId or EpicId from URL")
    return "epic", match.group(1)


def get_task(base_url: str, task_id: str, token: str, timeout: int) -> Dict[str, Any]:
    task_url = f"{base_url.rstrip('/')}/api/tasktracker/task/query/get/{task_id}"
    return http_get_json(task_url, token, timeout)

def get_epic(base_url: str, epic_id: str, token: str, timeout: int) -> Dict[str, Any]:
    epic_url = f"{base_url.rstrip('/')}/api/tasktracker/epic/query/get/{epic_id}"
    return http_get_json(epic_url, token, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get TaskTracker task or epic data by URL or ID using ERP client credentials token"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--url",
        help="Task or epic URL, e.g. <erp_base_url>/tasktracker/projects/{projectId}/tasks/{taskId} or /epics/{epicId}",
    )
    source_group.add_argument("--task-id", help="Task ID, e.g. 12345")
    source_group.add_argument("--epic-id", help="Epic ID, e.g. 191")
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL; required with --task-id/--epic-id when erp_base_url is not set in env/.env",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        entity_type: Literal["task", "epic"]
        entity_id: str

        if args.url:
            base_url, auth_base_url = derive_base_urls(args.url, invalid_message="Invalid TaskTracker URL")
            entity_type, entity_id = parse_url_entity(args.url)
        else:
            raw_entity_id = args.task_id if args.task_id is not None else args.epic_id
            entity_type = "task" if args.task_id is not None else "epic"
            entity_id = str(raw_entity_id).strip()
            if not re.fullmatch(r"[0-9]+", entity_id):
                if entity_type == "task":
                    raise ValueError("Task ID must contain only digits")
                raise ValueError("Epic ID must contain only digits")
            base_url, auth_base_url = derive_base_urls(
                get_base_url(args.erp_base_url),
                invalid_message="Invalid base URL",
            )

        token = get_token(auth_base_url, args.timeout)
        if entity_type == "task":
            task = get_task(base_url, entity_id, token, args.timeout)
            result = {
                "TaskId": entity_id,
                "Title": get_first_present_value(task, ("Title", "title")) if isinstance(task, dict) else None,
                "Description": get_first_present_value(task, ("Description", "description")) if isinstance(task, dict) else None,
            }
        else:
            epic = get_epic(base_url, entity_id, token, args.timeout)
            result = {
                "ID": int(entity_id),
                "Title": get_first_present_value(epic, ("Title", "title")) if isinstance(epic, dict) else None,
                "Description": get_first_present_value(epic, ("Description", "description")) if isinstance(epic, dict) else None,
                "ProjectId": get_first_present_value(epic, ("ProjectId", "projectId")) if isinstance(epic, dict) else None,
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

