#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


def parse_task_id(task_url: str) -> str:
    match = re.search(r"/tasks/([0-9]+)", task_url)
    if not match:
        raise ValueError("Cannot extract TaskId from URL")
    return match.group(1)


def derive_base_urls(task_url: str) -> Tuple[str, str]:
    parsed = urlparse(task_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid task URL")

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


def http_get_json(url: str, token: str, timeout: int) -> Dict[str, Any]:
    request = Request(url, method="GET")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/json")

    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


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


def get_task(base_url: str, task_id: str, token: str, timeout: int) -> Dict[str, Any]:
    task_url = f"{base_url.rstrip('/')}/api/tasktracker/task/query/get/{task_id}"
    return http_get_json(task_url, token, timeout)


def get_first_present_value(data: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


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
        base_url, auth_base_url = derive_base_urls(args.url)

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

