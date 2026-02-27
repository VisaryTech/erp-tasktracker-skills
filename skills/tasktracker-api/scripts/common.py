#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


def derive_base_urls(url: str, invalid_message: str = "Invalid base URL") -> Tuple[str, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(invalid_message)

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


def get_first_present_value(data: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def print_http_error(exc: HTTPError) -> None:
    body = ""
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = "<cannot-read-body>"
    print(
        f"API HTTP error: url={exc.url}, status={exc.code}, reason={exc.reason}, body={body}",
        file=sys.stderr,
    )


def print_network_error(exc: URLError) -> None:
    print(f"API network error: reason={exc.reason}", file=sys.stderr)


def print_execution_error(exc: Exception) -> None:
    print(f"Execution error: {exc}", file=sys.stderr)
