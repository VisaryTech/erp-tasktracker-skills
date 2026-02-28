#!/usr/bin/env python3
import argparse
import json
import re
from typing import Any, Dict, Literal, Tuple
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_base_url,
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

def get_task_comments(base_url: str, task_id: str, token: str, timeout: int) -> Any:
    comments_url = f"{base_url.rstrip('/')}/api/tasktracker/TaskComment?taskId={task_id}"
    return http_get_json(comments_url, token, timeout)

def get_epic_comments(base_url: str, epic_id: str, token: str, timeout: int) -> Any:
    comments_url = f"{base_url.rstrip('/')}/api/tasktracker/EpicComment?taskId={epic_id}"
    return http_get_json(comments_url, token, timeout)


def parse_entity_id(raw_value: Any, label: str) -> str:
    value = str(raw_value).strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{label} must contain only digits")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get TaskTracker task/epic data or task comments by URL or ID using ERP client credentials token"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--url",
        help="Task or epic URL, e.g. <erp_base_url>/tasktracker/projects/{projectId}/tasks/{taskId} or /epics/{epicId}",
    )
    source_group.add_argument("--task-id", help="Task ID")
    source_group.add_argument("--epic-id", help="Epic ID")
    source_group.add_argument("--task-comments-id", help="Task ID for comments list")
    source_group.add_argument("--epic-comments-id", help="Epic ID for comments list")
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL; required with --task-id/--epic-id/--task-comments-id/--epic-comments-id when erp_base_url is not set in env/.env",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        entity_type: Literal["task", "epic", "task_comments", "epic_comments"]
        entity_id: str

        if args.url:
            base_url, auth_base_url = derive_base_urls(args.url, invalid_message="Invalid TaskTracker URL")
            entity_type, entity_id = parse_url_entity(args.url)
        else:
            raw_entity_id = args.task_id if args.task_id is not None else args.epic_id
            if raw_entity_id is not None:
                entity_type = "task" if args.task_id is not None else "epic"
                entity_id = parse_entity_id(raw_entity_id, "Task ID" if entity_type == "task" else "Epic ID")
            elif args.task_comments_id is not None:
                entity_type = "task_comments"
                entity_id = parse_entity_id(args.task_comments_id, "Task comments ID")
            else:
                entity_type = "epic_comments"
                entity_id = parse_entity_id(args.epic_comments_id, "Epic comments ID")
            base_url, auth_base_url = derive_base_urls(
                get_base_url(args.erp_base_url),
                invalid_message="Invalid base URL",
            )

        token = get_token(auth_base_url, args.timeout)
        if entity_type == "task":
            result = get_task(base_url, entity_id, token, args.timeout)
        elif entity_type == "epic":
            result = get_epic(base_url, entity_id, token, args.timeout)
        elif entity_type == "task_comments":
            result = get_task_comments(base_url, entity_id, token, args.timeout)
        else:
            result = get_epic_comments(base_url, entity_id, token, args.timeout)

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

