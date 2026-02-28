#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError

from common import (
    derive_base_urls,
    get_base_url,
    get_token,
    http_post_json,
    load_env_from_dotenv,
    print_execution_error,
    print_http_error,
    print_network_error,
)


def build_comment_text(text: Optional[str], text_file: Optional[str]) -> str:
    if text and text_file:
        raise ValueError("Use either --text or --text-file, not both")

    if text_file:
        content = Path(text_file).read_text(encoding="utf-8")
    else:
        content = text or ""

    comment = content.strip()
    if not comment:
        raise ValueError("Comment text is empty")
    return comment


def parse_id(raw_value: str, label: str) -> int:
    value = str(raw_value).strip()
    if not value or not value.isdigit():
        raise ValueError(f"{label} must contain only digits")
    return int(value)


def parse_parent_id(raw_parent_id: Optional[str]) -> Optional[int]:
    if raw_parent_id is None:
        return None
    value = raw_parent_id.strip()
    if not value:
        return None
    if not value.isdigit():
        raise ValueError("Parent ID must contain only digits")
    return int(value)


def build_request(entity: str, entity_id: int, parent_id: Optional[int], text: str) -> Dict[str, Any]:
    normalized = entity.strip().lower()
    if normalized == "task":
        return {
            "url_path": "/api/tasktracker/taskComment/command/Create",
            "payload": {
                "taskId": entity_id,
                "parentId": parent_id,
                "text": text,
                "files": None,
            },
        }
    if normalized == "epic":
        return {
            "url_path": "/api/tasktracker/epicComment/command/create",
            "payload": {
                "epicId": entity_id,
                "parentId": parent_id,
                "text": text,
            },
        }
    raise ValueError("Entity must be 'task' or 'epic'")


def create_comment(base_url: str, token: str, request_data: Dict[str, Any], timeout: int) -> Any:
    create_url = f"{base_url.rstrip('/')}{request_data['url_path']}"
    return http_post_json(create_url, token, request_data["payload"], timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create TaskTracker task or epic comment"
    )
    parser.add_argument(
        "--entity",
        required=True,
        choices=["task", "epic"],
        help="Comment target entity type",
    )
    parser.add_argument(
        "--id",
        required=True,
        help="Entity ID (taskId or epicId)",
    )
    parser.add_argument(
        "--parent-id",
        help="Parent comment ID for reply mode; omit for top-level comment",
    )
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--text", help="Comment text")
    parser.add_argument("--text-file", help="Path to UTF-8 file with comment text")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        comment_text = build_comment_text(args.text, args.text_file)
        entity_id = parse_id(args.id, "Entity ID")
        parent_id = parse_parent_id(args.parent_id)
        request_data = build_request(args.entity, entity_id, parent_id, comment_text)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = create_comment(base_url, token, request_data, args.timeout)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    except FileNotFoundError as exc:
        print_execution_error(Exception(f"file not found: {exc}"))
        return 1
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
