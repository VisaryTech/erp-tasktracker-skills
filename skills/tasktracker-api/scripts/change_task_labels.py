#!/usr/bin/env python3
import argparse
import json
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_base_url,
    get_token,
    http_patch_json,
    load_env_from_dotenv,
    print_execution_error,
    print_http_error,
    print_network_error,
)


def parse_task_id(raw_value: str) -> int:
    value = str(raw_value).strip()
    if not value or not value.isdigit():
        raise ValueError("Task ID must contain only digits")
    return int(value)


def parse_label_ids(raw_value: str) -> List[int]:
    chunks = [chunk.strip() for chunk in raw_value.split(",")]
    values: List[int] = []
    for chunk in chunks:
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ValueError("label-ids must contain integers separated by commas")
        values.append(int(chunk))
    return values


def build_payload(task_id: int, label_ids_raw: str) -> Dict[str, Any]:
    return {
        "taskId": task_id,
        "labelIds": parse_label_ids(label_ids_raw),
    }


def change_task_labels(base_url: str, task_id: int, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    endpoint = f"{base_url.rstrip('/')}/api/tasktracker/Task/command/ChangeLabels/{task_id}"
    return http_patch_json(endpoint, token, payload, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Change labels for TaskTracker task"
    )
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument(
        "--label-ids",
        default="",
        help="Comma-separated label IDs; pass empty string to clear all labels",
    )
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        task_id = parse_task_id(args.task_id)
        payload = build_payload(task_id, args.label_ids)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = change_task_labels(base_url, task_id, token, payload, args.timeout)
        print(json.dumps(response, ensure_ascii=False, indent=2))
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
