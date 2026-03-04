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
    parse_int_env,
    print_execution_error,
    print_http_error,
    print_network_error,
)


STATUS_TO_ENV = {
    "checked": "erp_label_approved",
    "to-define": "erp_label_to_define",
}


def parse_epic_id(raw_value: str) -> int:
    value = str(raw_value).strip()
    if not value or not value.isdigit():
        raise ValueError("Epic ID must contain only digits")
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


def resolve_label_ids(args: argparse.Namespace) -> List[int]:
    if args.label_ids is not None:
        return parse_label_ids(args.label_ids)
    if args.status is None:
        raise ValueError("Either --status or --label-ids must be provided")
    return [parse_int_env(STATUS_TO_ENV[args.status])]


def build_payload(epic_id: int, label_ids: List[int]) -> Dict[str, Any]:
    return {
        "epicId": epic_id,
        "labelIds": label_ids,
    }


def change_epic_labels(base_url: str, epic_id: int, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    endpoint = f"{base_url.rstrip('/')}/api/tasktracker/epic/command/changeLabels/{epic_id}"
    return http_patch_json(endpoint, token, payload, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Change labels for TaskTracker epic or apply status labels from .env",
    )
    parser.add_argument("--epic-id", required=True, help="Epic ID")
    parser.add_argument(
        "--status",
        choices=["checked", "to-define"],
        help="Status preset: checked -> erp_label_approved, to-define -> erp_label_to_define",
    )
    parser.add_argument(
        "--label-ids",
        help="Comma-separated label IDs; overrides --status mapping when passed",
    )
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        epic_id = parse_epic_id(args.epic_id)
        label_ids = resolve_label_ids(args)
        payload = build_payload(epic_id, label_ids)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = change_epic_labels(base_url, epic_id, token, payload, args.timeout)
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
