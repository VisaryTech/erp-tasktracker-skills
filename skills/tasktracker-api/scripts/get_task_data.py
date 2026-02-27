#!/usr/bin/env python3
import argparse
import json
import re
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_first_present_value,
    get_token,
    http_get_json,
    load_env_from_dotenv,
    print_execution_error,
    print_http_error,
    print_network_error,
)


def parse_task_id(task_url: str) -> str:
    match = re.search(r"/tasks/([0-9]+)", task_url)
    if not match:
        raise ValueError("Cannot extract TaskId from URL")
    return match.group(1)


def get_task(base_url: str, task_id: str, token: str, timeout: int) -> Dict[str, Any]:
    task_url = f"{base_url.rstrip('/')}/api/tasktracker/task/query/get/{task_id}"
    return http_get_json(task_url, token, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get TaskTracker task data by URL using ERP client credentials token"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Task URL, e.g. <erp_base_url>/tasktracker/projects/{projectId}/tasks/{taskId}",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        base_url, auth_base_url = derive_base_urls(args.url, invalid_message="Invalid task URL")

        task_id = parse_task_id(args.url)
        token = get_token(auth_base_url, args.timeout)
        task = get_task(base_url, task_id, token, args.timeout)

        result = {
            "TaskId": task_id,
            "Title": get_first_present_value(task, ("Title", "title")) if isinstance(task, dict) else None,
            "Description": get_first_present_value(task, ("Description", "description")) if isinstance(task, dict) else None,
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

