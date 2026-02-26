#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


def derive_base_urls(base_url: str) -> Tuple[str, str]:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid base URL")

    host = parsed.netloc
    base_url = f"{parsed.scheme}://{host}"

    auth_host = host if host.startswith("id-") else f"id-{host}"
    auth_base_url = f"{parsed.scheme}://{auth_host}"

    return base_url, auth_base_url


def http_post_form(url: str, data: Dict[str, str], timeout: int) -> Dict[str, Any]:
    encoded = urlencode(data).encode("utf-8")
    request = Request(url, data=encoded, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def http_post_json(url: str, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=encoded, method="POST")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")

    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {"status": response.status}


def get_token(auth_base_url: str, timeout: int) -> str:
    client_id = os.getenv("erp_client_id")
    client_secret = os.getenv("erp_client_secret")

    if not client_id or not client_secret:
        raise RuntimeError("Missing env vars: erp_client_id and/or erp_client_secret")

    token_url = f"{auth_base_url.rstrip('/')}/oidc/connect/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    data = http_post_form(token_url, payload, timeout)
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Token response does not contain access_token")
    return str(token)


def load_env_from_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue

        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


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
        "--base-url",
        default="https://erp.visary.cloud",
        help="ERP base URL, default: https://erp.visary.cloud",
    )
    parser.add_argument("--text", help="Comment text")
    parser.add_argument("--text-file", help="Path to UTF-8 file with comment text")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        comment_text = build_comment_text(args.text, args.text_file)
        base_url, auth_base_url = derive_base_urls(args.base_url)
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
        print(f"Execution error: file not found: {exc}", file=sys.stderr)
        return 1
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = "<cannot-read-body>"
        print(
            f"API HTTP error: url={exc.url}, status={exc.code}, reason={exc.reason}, body={body}",
            file=sys.stderr,
        )
        return 1
    except URLError as exc:
        print(f"API network error: reason={exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Execution error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
