#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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


def get_base_url(cli_base_url: Optional[str]) -> str:
    raw_value = (
        cli_base_url
        or os.getenv("erp_base_url")
        or os.getenv("ERP_BASE_URL")
        or os.getenv("erp-base-url")
    )
    if not raw_value:
        raise ValueError("Base URL is required: pass --erp-base-url or set erp_base_url in .env")
    return raw_value.strip()


def parse_csv_ints(raw: Optional[str], arg_name: str) -> List[int]:
    if not raw:
        return []

    values: List[int] = []
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        if not value.isdigit():
            raise ValueError(f"{arg_name} must contain integers separated by commas")
        values.append(int(value))

    return values


def get_project_id(cli_value: Optional[int]) -> int:
    if cli_value is not None:
        return cli_value

    env_value = (
        os.getenv("erp_tasktracker_project_id")
        or os.getenv("erp-tasktracker-project-id")
        or os.getenv("project-id")
        or os.getenv("projectId")
    )
    if env_value is None:
        raise ValueError(
            "projectId is required: pass --project-id or set erp_tasktracker_project_id in .env"
        )

    env_value = env_value.strip()
    if not env_value.isdigit():
        raise ValueError("erp_tasktracker_project_id in .env must be an integer")
    return int(env_value)


def require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required and cannot be empty")
    return cleaned


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    title = require_non_empty(args.title, "Title")
    description = require_non_empty(args.description, "Description")
    project_id = get_project_id(args.project_id)

    payload: Dict[str, Any] = {
        "LabelIds": parse_csv_ints(args.label_ids, "label-ids"),
        "AssigneeIds": [],
        "CurrentAssigneeId": None,
        "Weight": args.weight,
        "Description": description,
        "Files": "",
        "SprintId": args.sprint_id,
        "MilestoneId": args.milestone_id,
        "TemplateId": None,
        "Title": title,
        "EpicId": args.epic_id,
        "projectId": project_id,
    }

    return payload


def create_task(base_url: str, token: str, payload: Dict[str, Any], timeout: int) -> Any:
    create_url = f"{base_url.rstrip('/')}/api/tasktracker/task/command/create"
    return http_post_json(create_url, token, payload, timeout)


def get_first_present_value(data: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create TaskTracker task using ERP client credentials token"
    )
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--description", required=True, help="Task description")
    parser.add_argument(
        "--project-id",
        type=int,
        help="Project ID (fallback: .env erp_tasktracker_project_id)",
    )
    parser.add_argument("--epic-id", type=int, help="Epic ID")
    parser.add_argument("--label-ids", help="Comma-separated label IDs, e.g. 6,73")
    parser.add_argument("--weight", type=int, help="Task weight")
    parser.add_argument("--sprint-id", type=int, help="Sprint ID")
    parser.add_argument("--milestone-id", type=int, help="Milestone ID")
    parser.add_argument(
        "--erp-base-url",
        help="ERP base URL (fallback: .env erp_base_url)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args()

    try:
        load_env_from_dotenv()
        payload = build_payload(args)
        base_url, auth_base_url = derive_base_urls(get_base_url(args.erp_base_url))
        token = get_token(auth_base_url, args.timeout)
        response = create_task(base_url, token, payload, args.timeout)

        if isinstance(response, dict):
            task_id = get_first_present_value(response, ("TaskId", "taskId", "Id", "id"))
            title = get_first_present_value(response, ("Title", "title")) or payload["Title"]
            description = (
                get_first_present_value(response, ("Description", "description"))
                or payload["Description"]
            )
            project_id = get_first_present_value(response, ("projectId", "ProjectId")) or payload["projectId"]
        else:
            task_id = None
            title = payload["Title"]
            description = payload["Description"]
            project_id = payload["projectId"]

        result = {
            "TaskId": task_id,
            "Title": title,
            "Description": description,
            "projectId": project_id,
            "baseUrl": base_url,
            "apiResponse": response,
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

