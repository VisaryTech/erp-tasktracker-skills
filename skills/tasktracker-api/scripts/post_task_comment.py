#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Optional
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


def create_task_comment(base_url: str, task_id: str, token: str, text: str, timeout: int) -> Any:
    create_url = f"{base_url.rstrip('/')}/api/tasktracker/taskComment/command/Create"
    payload = {
        "taskId": task_id,
        "parentId": None,
        "text": text,
        "files": None,
    }
    return http_post_json(create_url, token, payload, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create TaskTracker task comment by task ID"
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Task ID, e.g. 12345",
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
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        task_id = str(args.task_id).strip()
        if not task_id:
            raise ValueError("Task ID is empty")
        token = get_token(auth_base_url, args.timeout)
        response = create_task_comment(base_url, task_id, token, comment_text, args.timeout)

        result = {
            "taskId": task_id,
            "baseUrl": base_url,
            "commentText": comment_text,
            "apiResponse": response,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
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

