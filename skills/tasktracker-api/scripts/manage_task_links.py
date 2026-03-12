#!/usr/bin/env python3
import argparse
import json
from typing import Any, Dict
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


TASK_LINK_TYPE_MAP = {
    "0": 0,
    "1": 1,
    "2": 2,
    "relatesto": 0,
    "blocks": 1,
    "isblocked": 2,
    "relates-to": 0,
    "is-blocked": 2,
}


def parse_task_id(raw_value: str, label: str) -> int:
    value = str(raw_value).strip()
    if not value or not value.isdigit():
        raise ValueError(f"{label} must contain only digits")
    return int(value)


def parse_link_type(raw_value: str) -> int:
    key = str(raw_value).strip().lower()
    if key not in TASK_LINK_TYPE_MAP:
        raise ValueError(
            "Invalid link type. Use one of: 0|1|2, RelatesTo, Blocks, IsBlocked"
        )
    return TASK_LINK_TYPE_MAP[key]


def build_payload(action: str, task_id: int, other_task_id: int, link_type: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "taskId": task_id,
        "otherTaskId": other_task_id,
    }
    if action != "delete":
        payload["type"] = parse_link_type(link_type)
    return payload


def send_request(base_url: str, action: str, task_id: int, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    action_to_endpoint = {
        "create": f"/api/tasktracker/Task/command/CreateLink/{task_id}",
        "change-type": f"/api/tasktracker/Task/command/ChangeLinkType/{task_id}",
        "delete": f"/api/tasktracker/Task/command/DeleteLink/{task_id}",
    }
    url = f"{base_url.rstrip('/')}{action_to_endpoint[action]}"
    return http_patch_json(url, token, payload, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage TaskTracker task links",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["create", "change-type", "delete"],
        help="Link action: create | change-type | delete",
    )
    parser.add_argument("--task-id", required=True, help="Source task ID")
    parser.add_argument("--other-task-id", required=True, help="Linked task ID")
    parser.add_argument(
        "--type",
        default="",
        help="Link type for create/change-type: 0|1|2 or RelatesTo|Blocks|IsBlocked",
    )
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        task_id = parse_task_id(args.task_id, "Task ID")
        other_task_id = parse_task_id(args.other_task_id, "Other task ID")

        if args.action in ("create", "change-type") and not str(args.type).strip():
            raise ValueError("--type is required for create and change-type actions")

        payload = build_payload(args.action, task_id, other_task_id, args.type)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = send_request(base_url, args.action, task_id, token, payload, args.timeout)
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
