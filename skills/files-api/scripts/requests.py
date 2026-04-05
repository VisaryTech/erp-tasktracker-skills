import json
import socket
from dataclasses import dataclass
from urllib import error, parse, request as urllib_request


class RequestException(Exception):
    pass


class Timeout(RequestException):
    pass


class HTTPError(RequestException):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


@dataclass
class Response:
    status_code: int
    headers: dict[str, str]
    content: bytes
    url: str

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)


def _encode_params(params):
    if params is None:
        return ""
    return parse.urlencode(params, doseq=True)


def _prepare_body(data=None, json_body=None, headers=None):
    normalized_headers = dict(headers or {})
    if json_body is not None:
        normalized_headers.setdefault("Content-Type", "application/json")
        return json.dumps(json_body).encode("utf-8"), normalized_headers

    if data is None:
        return None, normalized_headers

    if isinstance(data, bytes):
        return data, normalized_headers

    if isinstance(data, str):
        return data.encode("utf-8"), normalized_headers

    normalized_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    return parse.urlencode(data, doseq=True).encode("utf-8"), normalized_headers


def _build_response(raw_response, url):
    return Response(
        status_code=getattr(raw_response, "status", raw_response.getcode()),
        headers=dict(raw_response.headers.items()),
        content=raw_response.read(),
        url=url,
    )


def request(method, url, params=None, json=None, data=None, headers=None, timeout=None):
    query_string = _encode_params(params)
    if query_string:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query_string}"

    body, normalized_headers = _prepare_body(data=data, json_body=json, headers=headers)
    http_request = urllib_request.Request(
        url=url,
        data=body,
        headers=normalized_headers,
        method=method.upper(),
    )

    try:
        with urllib_request.urlopen(http_request, timeout=timeout) as raw_response:
            return _build_response(raw_response, url)
    except error.HTTPError as exc:
        return _build_response(exc, url)
    except (error.URLError, socket.timeout, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, socket.timeout):
            raise Timeout(str(exc)) from exc
        raise RequestException(str(exc)) from exc


def post(url, data=None, headers=None, timeout=None):
    return request("POST", url, data=data, headers=headers, timeout=timeout)
