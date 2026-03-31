import json
import os
from urllib.parse import quote
from urllib.parse import urlparse

import requests


class TaskTrackerAPI:
    @staticmethod
    def _read_file(path):
        try:
            from pathlib import Path

            return Path(os.path.expanduser(path)).read_text(encoding="utf-8").strip()
        except Exception:
            return None

    @classmethod
    def _resolve_base_url(cls, config=None):
        config = config or {}
        resolved = (
            config.get("endpoint")
            or os.getenv("ERP_API_BASE_URL")
            or os.getenv("erp_tasktracker_api_base_url")
            or cls._read_file("~/.config/erp/api_base_url")
        )
        if not resolved:
            raise ValueError("Missing ERP endpoint")
        return resolved.rstrip("/")

    @classmethod
    def _derive_auth_base_url(cls, base_url):
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid base_url")
        auth_host = parsed.netloc if parsed.netloc.startswith("id-") else f"id-{parsed.netloc}"
        return f"{parsed.scheme}://{auth_host}"

    @classmethod
    def _resolve_token_url(cls, base_url, config=None):
        config = config or {}
        explicit_token_url = (
            config.get("tokenUrl")
            or os.getenv("ERP_TOKEN_URL")
            or os.getenv("erp_tasktracker_token_url")
            or cls._read_file("~/.config/erp/token_url")
        )
        if explicit_token_url:
            return explicit_token_url.rstrip("/")
        auth_base_url = cls._derive_auth_base_url(base_url)
        return f"{auth_base_url.rstrip('/')}/oidc/connect/token"

    @classmethod
    def _get_access_token(cls, base_url, timeout=30, config=None):
        client_id = (
            os.getenv("ERP_CLIENT_ID")
            or os.getenv("erp_client_id")
            or cls._read_file("~/.config/erp/client_id")
        )
        client_secret = (
            os.getenv("ERP_CLIENT_SECRET")
            or os.getenv("erp_client_secret")
            or cls._read_file("~/.config/erp/client_secret")
        )
        if not client_id or not client_secret:
            raise RuntimeError("Missing env vars: erp_client_id and/or erp_client_secret")

        token_url = cls._resolve_token_url(base_url, config=config)
        try:
            response = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError(f"Token request timed out after {timeout} seconds: {token_url}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Token request failed: {token_url}: {exc}") from exc

        if not response.ok:
            try:
                error_body = response.json()
            except ValueError:
                error_body = response.text
            raise requests.HTTPError(
                f"HTTP {response.status_code} for token request {token_url}: {error_body}",
                response=response,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(f"Failed to decode token response JSON for {token_url}: {exc}") from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Token response does not contain access_token")
        return str(access_token)

    def __init__(self, timeout=30, headers=None, config=None):
        self.config = dict(config or {})
        self.base_url = self._resolve_base_url(config=self.config)
        self.headers = dict(headers or {})
        self.timeout = timeout
        self.token = self._get_access_token(self.base_url, timeout=timeout, config=self.config)
        self._extra_query_params = None

    def call_by_python_method(self, python_method, *args, odata_params=None, **kwargs):
        method = getattr(self, python_method, None)
        if method is None:
            raise AttributeError(f"TaskTrackerAPI has no method {python_method}")
        previous_extra_query_params = self._extra_query_params
        self._extra_query_params = dict(odata_params or {})
        try:
            return method(*args, **kwargs)
        finally:
            self._extra_query_params = previous_extra_query_params

    def _request(self, method, path, *, params=None, json_body=None, data=None, headers=None):
        merged_params = {}
        if params:
            merged_params.update(params)
        if self._extra_query_params:
            merged_params.update(self._extra_query_params)
        if not merged_params:
            merged_params = None
        request_headers = dict(self.headers)
        if self.token is not None and "Authorization" not in request_headers:
            request_headers["Authorization"] = (
                self.token if str(self.token).startswith("Bearer ") else f"Bearer {self.token}"
            )
        if headers:
            request_headers.update(headers)
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                params=merged_params,
                json=json_body,
                data=data,
                headers=request_headers,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError(f"Request timed out after {self.timeout} seconds: {method} {path}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Request failed: {method} {path}: {exc}") from exc

        if not response.ok:
            try:
                error_body = response.json()
            except ValueError:
                error_body = response.text
            raise requests.HTTPError(
                f"HTTP {response.status_code} for {method} {path}: {error_body}",
                response=response,
            )

        if response.status_code in (204, 205) or not response.content:
            return None

        content_type = response.headers.get("Content-Type", "")
        expects_json = any(token in content_type for token in ("application/json", "+json", "text/json"))
        if expects_json:
            try:
                return response.json()
            except ValueError as exc:
                raise ValueError(f"Failed to decode JSON response for {method} {path}: {exc}") from exc

        try:
            return response.json()
        except ValueError:
            return response.text if response.text != "" else None

    def get_board(self, *, project_id=None):
        """
        Get
        """
        path = f"/Board"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_board(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Board"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_board_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Board/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_query_get_board_id(self, board_id):
        """
        Get
        """
        path = f"/Board/query/Get/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_query_get_object_permissions_board_id(self, board_id):
        """
        GetObjectPermissions
        """
        path = f"/Board/query/GetObjectPermissions/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_query_get_type_permissions(self, *, project_id=None):
        """
        GetTypePermissions
        """
        path = f"/Board/query/GetTypePermissions"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_board_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Board/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_command_update_board_id(self, board_id, *, body=None):
        """
        Update
        """
        path = f"/Board/command/Update/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_board_command_delete_board_id(self, board_id):
        """
        Delete
        """
        path = f"/Board/command/Delete/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_board_command_restore_board_id(self, board_id):
        """
        Restore
        """
        path = f"/Board/command/Restore/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_list_query_get_lists_board_id(self, board_id):
        """
        GetLists
        """
        path = f"/BoardList/query/GetLists/{quote(str(board_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_list_query_get_labeled_list_list_id(self, list_id):
        """
        GetLabeledList
        """
        path = f"/BoardList/query/GetLabeledList/{quote(str(list_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_board_list_query_get_system_list_list_id(self, list_id):
        """
        GetSystemList
        """
        path = f"/BoardList/query/GetSystemList/{quote(str(list_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_board_list_command_create_list(self, *, body=None):
        """
        CreateList
        """
        path = f"/BoardList/command/CreateList"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_change_list_position(self, *, body=None):
        """
        ChangeListPosition
        """
        path = f"/BoardList/command/ChangeListPosition"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_board_list_command_delete_list_list_id(self, list_id):
        """
        DeleteList
        """
        path = f"/BoardList/command/DeleteList/{quote(str(list_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_change_position_in_labeled_list_task_id(self, task_id, *, body=None):
        """
        ChangePositionInLabeledList
        """
        path = f"/BoardList/command/ChangePositionInLabeledList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_change_position_in_system_list_task_id(self, task_id, *, body=None):
        """
        ChangePositionInSystemList
        """
        path = f"/BoardList/command/ChangePositionInSystemList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_move_task_from_labeled_to_labeled_list_task_id(self, task_id, *, body=None):
        """
        MoveTaskFromLabeledToLabeledList
        """
        path = f"/BoardList/command/MoveTaskFromLabeledToLabeledList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_move_task_from_labeled_to_system_list_task_id(self, task_id, *, body=None):
        """
        MoveTaskFromLabeledToSystemList
        """
        path = f"/BoardList/command/MoveTaskFromLabeledToSystemList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_move_task_from_system_to_labeled_list_task_id(self, task_id, *, body=None):
        """
        MoveTaskFromSystemToLabeledList
        """
        path = f"/BoardList/command/MoveTaskFromSystemToLabeledList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_board_list_command_move_task_from_system_to_system_list_task_id(self, task_id, *, body=None):
        """
        MoveTaskFromSystemToSystemList
        """
        path = f"/BoardList/command/MoveTaskFromSystemToSystemList/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic(self, *, project_id=None):
        """
        Get
        """
        path = f"/Epic"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Epic"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Epic/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_comment(self, *, task_id=None):
        """
        Get
        """
        path = f"/EpicComment"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_comment(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/EpicComment"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_comment_count(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/EpicComment/$count"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_comment_query_get_comment_id(self, comment_id):
        """
        Get
        """
        path = f"/EpicComment/query/Get/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_comment_query_get_object_permissions_comment_id(self, comment_id):
        """
        GetObjectPermissions
        """
        path = f"/EpicComment/query/GetObjectPermissions/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_comment_query_get_type_permissions(self, *, epic_id=None):
        """
        GetTypePermissions
        """
        path = f"/EpicComment/query/GetTypePermissions"
        query_params = {}
        if epic_id is not None:
            query_params["epicId"] = epic_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_epic_comment_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/EpicComment/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_comment_command_change_text_comment_id(self, comment_id, *, body=None):
        """
        ChangeText
        """
        path = f"/EpicComment/command/ChangeText/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_comment_command_change_files_comment_id(self, comment_id, *, body=None):
        """
        ChangeFiles
        """
        path = f"/EpicComment/command/ChangeFiles/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_epic_comment_command_delete_comment_id(self, comment_id):
        """
        Delete
        """
        path = f"/EpicComment/command/Delete/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_epic_comment_command_restore_comment_id(self, comment_id):
        """
        Restore
        """
        path = f"/EpicComment/command/Restore/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_query_get_epic_id(self, epic_id):
        """
        Get
        """
        path = f"/Epic/query/Get/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_query_get_metrics_epic_id(self, epic_id):
        """
        GetMetrics
        """
        path = f"/Epic/query/GetMetrics/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_query_get_object_permissions_epic_id(self, epic_id):
        """
        GetObjectPermissions
        """
        path = f"/Epic/query/GetObjectPermissions/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_query_get_type_permissions(self, *, project_id=None):
        """
        GetTypePermissions
        """
        path = f"/Epic/query/GetTypePermissions"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_epic_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Epic/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_title_epic_id(self, epic_id, *, body=None):
        """
        ChangeTitle
        """
        path = f"/Epic/command/ChangeTitle/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_description_epic_id(self, epic_id, *, body=None):
        """
        ChangeDescription
        """
        path = f"/Epic/command/ChangeDescription/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_files_epic_id(self, epic_id, *, body=None):
        """
        ChangeFiles
        """
        path = f"/Epic/command/ChangeFiles/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_period_epic_id(self, epic_id, *, body=None):
        """
        ChangePeriod
        """
        path = f"/Epic/command/ChangePeriod/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_milestone_epic_id(self, epic_id, *, body=None):
        """
        ChangeMilestone
        """
        path = f"/Epic/command/ChangeMilestone/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_labels_epic_id(self, epic_id, *, body=None):
        """
        ChangeLabels
        """
        path = f"/Epic/command/ChangeLabels/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_add_label_epic_id(self, epic_id, *, body=None):
        """
        AddLabel
        """
        path = f"/Epic/command/AddLabel/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_reopen_epic_id(self, epic_id):
        """
        Reopen
        """
        path = f"/Epic/command/Reopen/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_close_epic_id(self, epic_id):
        """
        Close
        """
        path = f"/Epic/command/Close/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_epic_command_delete_epic_id(self, epic_id):
        """
        Delete
        """
        path = f"/Epic/command/Delete/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_epic_command_restore_epic_id(self, epic_id):
        """
        Restore
        """
        path = f"/Epic/command/Restore/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_parent_epic_id(self, epic_id, *, body=None):
        """
        ChangeParent
        """
        path = f"/Epic/command/ChangeParent/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_epic_command_change_roadmap_order_epic_id(self, epic_id, *, body=None):
        """
        ChangeRoadmapOrder
        """
        path = f"/Epic/command/ChangeRoadmapOrder/{quote(str(epic_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_for_task_registry(self):
        """
        Get
        """
        path = f"/EpicForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/EpicForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/EpicForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_epic_history(self, *, task_id=None):
        """
        Get
        """
        path = f"/EpicHistory"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_history(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/EpicHistory"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_epic_history_count(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/EpicHistory/$count"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/Label"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/odata/Label"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_count(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/odata/Label/$count"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_query_get_label_id(self, label_id):
        """
        Get
        """
        path = f"/Label/query/Get/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_query_get_object_permissions_label_id(self, label_id):
        """
        GetObjectPermissions
        """
        path = f"/Label/query/GetObjectPermissions/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_query_get_type_permissions(self, *, scope_type=None, scope_id=None):
        """
        GetTypePermissions
        """
        path = f"/Label/query/GetTypePermissions"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_label_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Label/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_label_command_update_label_id(self, label_id, *, body=None):
        """
        Update
        """
        path = f"/Label/command/Update/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_label_command_promote_label_id(self, label_id, *, body=None):
        """
        Promote
        """
        path = f"/Label/command/Promote/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_label_command_delete_label_id(self, label_id):
        """
        Delete
        """
        path = f"/Label/command/Delete/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_label_command_restore_label_id(self, label_id):
        """
        Restore
        """
        path = f"/Label/command/Restore/{quote(str(label_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_for_group(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/LabelForGroup"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_group(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/LabelForGroup"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_group_count(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/LabelForGroup/$count"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_for_project(self, *, project_id=None):
        """
        Get
        """
        path = f"/LabelForProject"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_project(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/LabelForProject"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_project_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/LabelForProject/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_label_for_task_registry(self):
        """
        Get
        """
        path = f"/LabelForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/LabelForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_label_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/LabelForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_metadata(self):
        """
        GetMetadata
        """
        path = f"/odata/$metadata"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata(self):
        """
        GetServiceDocument
        """
        path = f"/odata"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_milestone(self, *, project_id=None):
        """
        Get
        """
        path = f"/Milestone"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_milestone(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Milestone"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_milestone_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Milestone/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_milestone_query_get_milestone_id(self, milestone_id):
        """
        Get
        """
        path = f"/Milestone/query/Get/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_milestone_query_get_object_permissions_milestone_id(self, milestone_id):
        """
        GetObjectPermissions
        """
        path = f"/Milestone/query/GetObjectPermissions/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_milestone_query_get_type_permissions(self, *, project_id=None):
        """
        GetTypePermissions
        """
        path = f"/Milestone/query/GetTypePermissions"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_milestone_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Milestone/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_milestone_command_update_milestone_id(self, milestone_id, *, body=None):
        """
        Update
        """
        path = f"/Milestone/command/Update/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_milestone_command_reopen_milestone_id(self, milestone_id):
        """
        Reopen
        """
        path = f"/Milestone/command/Reopen/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_milestone_command_close_milestone_id(self, milestone_id):
        """
        Close
        """
        path = f"/Milestone/command/Close/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_milestone_command_delete_milestone_id(self, milestone_id):
        """
        Delete
        """
        path = f"/Milestone/command/Delete/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_milestone_command_restore_milestone_id(self, milestone_id):
        """
        Restore
        """
        path = f"/Milestone/command/Restore/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_milestone_command_change_roadmap_order_milestone_id(self, milestone_id, *, body=None):
        """
        ChangeRoadmapOrder
        """
        path = f"/Milestone/command/ChangeRoadmapOrder/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_milestone_for_task_registry(self):
        """
        Get
        """
        path = f"/MilestoneForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_milestone_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/MilestoneForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_milestone_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/MilestoneForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project(self):
        """
        Get
        """
        path = f"/Project"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project(self):
        """
        Get
        """
        path = f"/odata/Project"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_count(self):
        """
        Get
        """
        path = f"/odata/Project/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_accessible_for_user(self):
        """
        Get
        """
        path = f"/ProjectAccessibleForUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_accessible_for_user(self):
        """
        Get
        """
        path = f"/odata/ProjectAccessibleForUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_accessible_for_user_count(self):
        """
        Get
        """
        path = f"/odata/ProjectAccessibleForUser/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_query_get_project_id(self, project_id):
        """
        Get
        """
        path = f"/Project/query/Get/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_query_get_object_permissions_project_id(self, project_id):
        """
        GetObjectPermissions
        """
        path = f"/Project/query/GetObjectPermissions/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_query_get_type_permissions(self, *, group_id=None):
        """
        GetTypePermissions
        """
        path = f"/Project/query/GetTypePermissions"
        query_params = {}
        if group_id is not None:
            query_params["groupId"] = group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Project/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_title_project_id(self, project_id, *, body=None):
        """
        ChangeTitle
        """
        path = f"/Project/command/ChangeTitle/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_description_project_id(self, project_id, *, body=None):
        """
        ChangeDescription
        """
        path = f"/Project/command/ChangeDescription/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_group_project_id(self, project_id, *, body=None):
        """
        ChangeGroup
        """
        path = f"/Project/command/ChangeGroup/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_labels_project_id(self, project_id, *, body=None):
        """
        ChangeLabels
        """
        path = f"/Project/command/ChangeLabels/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_privacy_level_project_id(self, project_id, *, body=None):
        """
        ChangePrivacyLevel
        """
        path = f"/Project/command/ChangePrivacyLevel/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_priority_project_id(self, project_id, *, body=None):
        """
        ChangePriority
        """
        path = f"/Project/command/ChangePriority/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_period_project_id(self, project_id, *, body=None):
        """
        ChangePeriod
        """
        path = f"/Project/command/ChangePeriod/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_avatar_project_id(self, project_id, *, body=None):
        """
        ChangeAvatar
        """
        path = f"/Project/command/ChangeAvatar/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_change_files_project_id(self, project_id, *, body=None):
        """
        ChangeFiles
        """
        path = f"/Project/command/ChangeFiles/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_reopen_project_id(self, project_id):
        """
        Reopen
        """
        path = f"/Project/command/Reopen/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_command_close_project_id(self, project_id):
        """
        Close
        """
        path = f"/Project/command/Close/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_project_command_delete_project_id(self, project_id):
        """
        Delete
        """
        path = f"/Project/command/Delete/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_command_restore_project_id(self, project_id):
        """
        Restore
        """
        path = f"/Project/command/Restore/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_command_add_to_favorites_project_id(self, project_id):
        """
        AddToFavorites
        """
        path = f"/Project/command/AddToFavorites/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_command_remove_from_favorites_project_id(self, project_id):
        """
        RemoveFromFavorites
        """
        path = f"/Project/command/RemoveFromFavorites/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_for_task_registry(self):
        """
        Get
        """
        path = f"/ProjectForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/ProjectForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/ProjectForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group(self):
        """
        Get
        """
        path = f"/ProjectGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_group(self):
        """
        Get
        """
        path = f"/odata/ProjectGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_group_count(self):
        """
        Get
        """
        path = f"/odata/ProjectGroup/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group_query_get_group_id(self, group_id):
        """
        Get
        """
        path = f"/ProjectGroup/query/Get/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group_query_get_object_permissions_group_id(self, group_id):
        """
        GetObjectPermissions
        """
        path = f"/ProjectGroup/query/GetObjectPermissions/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group_query_get_type_permissions(self):
        """
        GetTypePermissions
        """
        path = f"/ProjectGroup/query/GetTypePermissions"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/ProjectGroup/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_group_command_change_title_group_id(self, group_id, *, body=None):
        """
        ChangeTitle
        """
        path = f"/ProjectGroup/command/ChangeTitle/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_group_command_change_description_group_id(self, group_id, *, body=None):
        """
        ChangeDescription
        """
        path = f"/ProjectGroup/command/ChangeDescription/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_group_command_change_privacy_level_group_id(self, group_id, *, body=None):
        """
        ChangePrivacyLevel
        """
        path = f"/ProjectGroup/command/ChangePrivacyLevel/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_project_group_command_delete_group_id(self, group_id):
        """
        Delete
        """
        path = f"/ProjectGroup/command/Delete/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_command_restore_group_id(self, group_id):
        """
        Restore
        """
        path = f"/ProjectGroup/command/Restore/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group_membership_query_get_resulting_membership(self, *, user_id=None, project_group_id=None):
        """
        GetResultingMembership
        """
        path = f"/ProjectGroupMembership/query/GetResultingMembership"
        query_params = {}
        if user_id is not None:
            query_params["userId"] = user_id
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_group_membership_query_get_group_id(self, group_id):
        """
        Get
        """
        path = f"/ProjectGroupMembership/query/Get/{quote(str(group_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_join(self, *, body=None):
        """
        Join
        """
        path = f"/ProjectGroupMembership/command/Join"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_leave(self, *, body=None):
        """
        Leave
        """
        path = f"/ProjectGroupMembership/command/Leave"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_add_user(self, *, body=None):
        """
        AddUser
        """
        path = f"/ProjectGroupMembership/command/AddUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_add_user_group(self, *, body=None):
        """
        AddUserGroup
        """
        path = f"/ProjectGroupMembership/command/AddUserGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_change_user_access_level(self, *, body=None):
        """
        ChangeUserAccessLevel
        """
        path = f"/ProjectGroupMembership/command/ChangeUserAccessLevel"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_change_user_group_access_level(self, *, body=None):
        """
        ChangeUserGroupAccessLevel
        """
        path = f"/ProjectGroupMembership/command/ChangeUserGroupAccessLevel"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_remove_user(self, *, body=None):
        """
        RemoveUser
        """
        path = f"/ProjectGroupMembership/command/RemoveUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_group_membership_command_remove_user_group(self, *, body=None):
        """
        RemoveUserGroup
        """
        path = f"/ProjectGroupMembership/command/RemoveUserGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_in_registry(self, *, kind=None, query_mode=None, group_id=None, search=None):
        """
        Get
        """
        path = f"/ProjectInRegistry"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if query_mode is not None:
            query_params["queryMode"] = query_mode
        if group_id is not None:
            query_params["groupId"] = group_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_in_registry(self, *, kind=None, query_mode=None, group_id=None, search=None):
        """
        Get
        """
        path = f"/odata/ProjectInRegistry"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if query_mode is not None:
            query_params["queryMode"] = query_mode
        if group_id is not None:
            query_params["groupId"] = group_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_in_registry_count(self, *, kind=None, query_mode=None, group_id=None, search=None):
        """
        Get
        """
        path = f"/odata/ProjectInRegistry/$count"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if query_mode is not None:
            query_params["queryMode"] = query_mode
        if group_id is not None:
            query_params["groupId"] = group_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_membership_query_get_resulting_membership(self, *, user_id=None, project_id=None):
        """
        GetResultingMembership
        """
        path = f"/ProjectMembership/query/GetResultingMembership"
        query_params = {}
        if user_id is not None:
            query_params["userId"] = user_id
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_membership_query_get_permissions_project_id(self, project_id):
        """
        GetPermissions
        """
        path = f"/ProjectMembership/query/GetPermissions/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_join(self, *, body=None):
        """
        Join
        """
        path = f"/ProjectMembership/command/Join"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_leave(self, *, body=None):
        """
        Leave
        """
        path = f"/ProjectMembership/command/Leave"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_add_user(self, *, body=None):
        """
        AddUser
        """
        path = f"/ProjectMembership/command/AddUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_add_user_group(self, *, body=None):
        """
        AddUserGroup
        """
        path = f"/ProjectMembership/command/AddUserGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_change_user_access_level(self, *, body=None):
        """
        ChangeUserAccessLevel
        """
        path = f"/ProjectMembership/command/ChangeUserAccessLevel"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_change_user_group_access_level(self, *, body=None):
        """
        ChangeUserGroupAccessLevel
        """
        path = f"/ProjectMembership/command/ChangeUserGroupAccessLevel"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_remove_user(self, *, body=None):
        """
        RemoveUser
        """
        path = f"/ProjectMembership/command/RemoveUser"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_membership_command_remove_user_group(self, *, body=None):
        """
        RemoveUserGroup
        """
        path = f"/ProjectMembership/command/RemoveUserGroup"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_template(self):
        """
        Get
        """
        path = f"/ProjectTemplate"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_template(self):
        """
        Get
        """
        path = f"/odata/ProjectTemplate"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_template_count(self):
        """
        Get
        """
        path = f"/odata/ProjectTemplate/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_template_query_get_template_id(self, template_id):
        """
        Get
        """
        path = f"/ProjectTemplate/query/Get/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_template_query_get_object_permissions_template_id(self, template_id):
        """
        GetObjectPermissions
        """
        path = f"/ProjectTemplate/query/GetObjectPermissions/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_template_query_get_type_permissions(self):
        """
        GetTypePermissions
        """
        path = f"/ProjectTemplate/query/GetTypePermissions"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_template_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/ProjectTemplate/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_project_template_command_update_template_id(self, template_id, *, body=None):
        """
        Update
        """
        path = f"/ProjectTemplate/command/Update/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_project_template_command_delete_template_id(self, template_id):
        """
        Delete
        """
        path = f"/ProjectTemplate/command/Delete/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_project_template_command_restore_template_id(self, template_id):
        """
        Restore
        """
        path = f"/ProjectTemplate/command/Restore/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_project_with_membership(self):
        """
        Get
        """
        path = f"/ProjectWithMembership"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_with_membership(self):
        """
        Get
        """
        path = f"/odata/ProjectWithMembership"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_project_with_membership_count(self):
        """
        Get
        """
        path = f"/odata/ProjectWithMembership/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint(self, *, project_id=None):
        """
        Get
        """
        path = f"/Sprint"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_sprint(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Sprint"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_sprint_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/Sprint/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_sprint_id(self, sprint_id):
        """
        Get
        """
        path = f"/Sprint/query/Get/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_burndown_chart_sprint_id(self, sprint_id):
        """
        GetBurndownChart
        """
        path = f"/Sprint/query/GetBurndownChart/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_burnup_chart_sprint_id(self, sprint_id):
        """
        GetBurnupChart
        """
        path = f"/Sprint/query/GetBurnupChart/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_current_sprint_project_id(self, project_id):
        """
        GetCurrentSprint
        """
        path = f"/Sprint/query/GetCurrentSprint/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_object_permissions_sprint_id(self, sprint_id):
        """
        GetObjectPermissions
        """
        path = f"/Sprint/query/GetObjectPermissions/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_query_get_type_permissions(self, *, project_id=None):
        """
        GetTypePermissions
        """
        path = f"/Sprint/query/GetTypePermissions"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_sprint_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Sprint/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_sprint_command_update_sprint_id(self, sprint_id, *, body=None):
        """
        Update
        """
        path = f"/Sprint/command/Update/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_sprint_command_delete_sprint_id(self, sprint_id):
        """
        Delete
        """
        path = f"/Sprint/command/Delete/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_sprint_command_restore_sprint_id(self, sprint_id):
        """
        Restore
        """
        path = f"/Sprint/command/Restore/{quote(str(sprint_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_sprint_for_task_registry(self):
        """
        Get
        """
        path = f"/SprintForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_sprint_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/SprintForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_sprint_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/SprintForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task(self, *, project_id=None, search=None):
        """
        Get
        """
        path = f"/Task"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task(self, *, project_id=None, search=None):
        """
        Get
        """
        path = f"/odata/Task"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_count(self, *, project_id=None, search=None):
        """
        Get
        """
        path = f"/odata/Task/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_comment(self, *, task_id=None):
        """
        Get
        """
        path = f"/TaskComment"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_comment(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskComment"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_comment_count(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskComment/$count"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_comment_query_get_comment_id(self, comment_id):
        """
        Get
        """
        path = f"/TaskComment/query/Get/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_comment_query_get_object_permissions_comment_id(self, comment_id):
        """
        GetObjectPermissions
        """
        path = f"/TaskComment/query/GetObjectPermissions/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_comment_query_get_type_permissions(self, *, task_id=None):
        """
        GetTypePermissions
        """
        path = f"/TaskComment/query/GetTypePermissions"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_comment_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/TaskComment/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_comment_command_change_text_comment_id(self, comment_id, *, body=None):
        """
        ChangeText
        """
        path = f"/TaskComment/command/ChangeText/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_comment_command_change_files_comment_id(self, comment_id, *, body=None):
        """
        ChangeFiles
        """
        path = f"/TaskComment/command/ChangeFiles/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_task_comment_command_delete_comment_id(self, comment_id):
        """
        Delete
        """
        path = f"/TaskComment/command/Delete/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_comment_command_restore_comment_id(self, comment_id):
        """
        Restore
        """
        path = f"/TaskComment/command/Restore/{quote(str(comment_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_task_id(self, task_id):
        """
        Get
        """
        path = f"/Task/query/Get/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_all_project_tasks_assignees_project_id(self, project_id):
        """
        GetAllProjectTasksAssignees
        """
        path = f"/Task/query/GetAllProjectTasksAssignees/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_task_assignee_candidates_project_id(self, project_id):
        """
        GetTaskAssigneeCandidates
        """
        path = f"/Task/query/GetTaskAssigneeCandidates/{quote(str(project_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_task_participants_task_id(self, task_id):
        """
        GetTaskParticipants
        """
        path = f"/Task/query/GetTaskParticipants/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_task_assignees_task_id(self, task_id):
        """
        GetTaskAssignees
        """
        path = f"/Task/query/GetTaskAssignees/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_blocking_tasks_task_id(self, task_id):
        """
        GetBlockingTasks
        """
        path = f"/Task/query/GetBlockingTasks/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_all_milestone_tasks_assignees_milestone_id(self, milestone_id):
        """
        GetAllMilestoneTasksAssignees
        """
        path = f"/Task/query/GetAllMilestoneTasksAssignees/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_all_milestone_tasks_labels_milestone_id(self, milestone_id):
        """
        GetAllMilestoneTasksLabels
        """
        path = f"/Task/query/GetAllMilestoneTasksLabels/{quote(str(milestone_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_object_permissions_task_id(self, task_id):
        """
        GetObjectPermissions
        """
        path = f"/Task/query/GetObjectPermissions/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_query_get_type_permissions(self, *, project_id=None):
        """
        GetTypePermissions
        """
        path = f"/Task/query/GetTypePermissions"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/Task/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_title_task_id(self, task_id, *, body=None):
        """
        ChangeTitle
        """
        path = f"/Task/command/ChangeTitle/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_description_task_id(self, task_id, *, body=None):
        """
        ChangeDescription
        """
        path = f"/Task/command/ChangeDescription/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_reopen_task_id(self, task_id):
        """
        Reopen
        """
        path = f"/Task/command/Reopen/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_close_task_id(self, task_id):
        """
        Close
        """
        path = f"/Task/command/Close/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_period_task_id(self, task_id, *, body=None):
        """
        ChangePeriod
        """
        path = f"/Task/command/ChangePeriod/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_parent_task_id(self, task_id, *, body=None):
        """
        ChangeParent
        """
        path = f"/Task/command/ChangeParent/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_milestone_task_id(self, task_id, *, body=None):
        """
        ChangeMilestone
        """
        path = f"/Task/command/ChangeMilestone/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_sprint_task_id(self, task_id, *, body=None):
        """
        ChangeSprint
        """
        path = f"/Task/command/ChangeSprint/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_epic_task_id(self, task_id, *, body=None):
        """
        ChangeEpic
        """
        path = f"/Task/command/ChangeEpic/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_progress_task_id(self, task_id, *, body=None):
        """
        ChangeProgress
        """
        path = f"/Task/command/ChangeProgress/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_weight_task_id(self, task_id, *, body=None):
        """
        ChangeWeight
        """
        path = f"/Task/command/ChangeWeight/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_files_task_id(self, task_id, *, body=None):
        """
        ChangeFiles
        """
        path = f"/Task/command/ChangeFiles/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_labels_task_id(self, task_id, *, body=None):
        """
        ChangeLabels
        """
        path = f"/Task/command/ChangeLabels/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_add_label_task_id(self, task_id, *, body=None):
        """
        AddLabel
        """
        path = f"/Task/command/AddLabel/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_assignees_task_id(self, task_id, *, body=None):
        """
        ChangeAssignees
        """
        path = f"/Task/command/ChangeAssignees/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_current_assignee_task_id(self, task_id, *, body=None):
        """
        ChangeCurrentAssignee
        """
        path = f"/Task/command/ChangeCurrentAssignee/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_task_command_delete_task_id(self, task_id):
        """
        Delete
        """
        path = f"/Task/command/Delete/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_command_restore_task_id(self, task_id):
        """
        Restore
        """
        path = f"/Task/command/Restore/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_create_link_task_id(self, task_id, *, body=None):
        """
        CreateLink
        """
        path = f"/Task/command/CreateLink/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_change_link_type_task_id(self, task_id, *, body=None):
        """
        ChangeLinkType
        """
        path = f"/Task/command/ChangeLinkType/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_delete_link_task_id(self, task_id, *, body=None):
        """
        DeleteLink
        """
        path = f"/Task/command/DeleteLink/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_duplicate_to_project_task_id(self, task_id, *, body=None):
        """
        DuplicateToProject
        """
        path = f"/Task/command/DuplicateToProject/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_move_to_project_task_id(self, task_id, *, body=None):
        """
        MoveToProject
        """
        path = f"/Task/command/MoveToProject/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_command_subscribe_task_id(self, task_id):
        """
        Subscribe
        """
        path = f"/Task/command/Subscribe/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_command_unsubscribe_task_id(self, task_id):
        """
        Unsubscribe
        """
        path = f"/Task/command/Unsubscribe/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_command_bulk_edit(self, *, body=None):
        """
        BulkEdit
        """
        path = f"/Task/command/BulkEdit"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_history(self, *, task_id=None):
        """
        Get
        """
        path = f"/TaskHistory"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_history(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskHistory"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_history_count(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskHistory/$count"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_in_board_labeled_list(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/TaskInBoardLabeledList"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_board_labeled_list(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/odata/TaskInBoardLabeledList"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_board_labeled_list_count(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/odata/TaskInBoardLabeledList/$count"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_in_board_system_list(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/TaskInBoardSystemList"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_board_system_list(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/odata/TaskInBoardSystemList"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_board_system_list_count(self, *, board_list_id=None):
        """
        Get
        """
        path = f"/odata/TaskInBoardSystemList/$count"
        query_params = {}
        if board_list_id is not None:
            query_params["boardListId"] = board_list_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_in_epic(self, *, epic_id=None):
        """
        Get
        """
        path = f"/TaskInEpic"
        query_params = {}
        if epic_id is not None:
            query_params["epicId"] = epic_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_epic(self, *, epic_id=None):
        """
        Get
        """
        path = f"/odata/TaskInEpic"
        query_params = {}
        if epic_id is not None:
            query_params["epicId"] = epic_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_epic_count(self, *, epic_id=None):
        """
        Get
        """
        path = f"/odata/TaskInEpic/$count"
        query_params = {}
        if epic_id is not None:
            query_params["epicId"] = epic_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_in_registry(self, *, kind=None, search=None):
        """
        Get
        """
        path = f"/TaskInRegistry"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_registry(self, *, kind=None, search=None):
        """
        Get
        """
        path = f"/odata/TaskInRegistry"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_in_registry_count(self, *, kind=None, search=None):
        """
        Get
        """
        path = f"/odata/TaskInRegistry/$count"
        query_params = {}
        if kind is not None:
            query_params["kind"] = kind
        if search is not None:
            query_params["search"] = search
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_template(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/TaskTemplate"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_template(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/odata/TaskTemplate"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_template_count(self, *, scope_type=None, scope_id=None):
        """
        Get
        """
        path = f"/odata/TaskTemplate/$count"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_template_query_get_template_id(self, template_id):
        """
        Get
        """
        path = f"/TaskTemplate/query/Get/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_template_query_get_object_permissions_template_id(self, template_id):
        """
        GetObjectPermissions
        """
        path = f"/TaskTemplate/query/GetObjectPermissions/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_template_query_get_type_permissions(self, *, scope_type=None, scope_id=None):
        """
        GetTypePermissions
        """
        path = f"/TaskTemplate/query/GetTypePermissions"
        query_params = {}
        if scope_type is not None:
            query_params["scopeType"] = scope_type
        if scope_id is not None:
            query_params["scopeId"] = scope_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_template_command_create(self, *, body=None):
        """
        Create
        """
        path = f"/TaskTemplate/command/Create"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_template_command_update_template_id(self, template_id, *, body=None):
        """
        Update
        """
        path = f"/TaskTemplate/command/Update/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_task_template_command_delete_template_id(self, template_id):
        """
        Delete
        """
        path = f"/TaskTemplate/command/Delete/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_template_command_restore_template_id(self, template_id):
        """
        Restore
        """
        path = f"/TaskTemplate/command/Restore/{quote(str(template_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_template_for_project(self, *, project_id=None):
        """
        Get
        """
        path = f"/TaskTemplateForProject"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_template_for_project(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/TaskTemplateForProject"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_template_for_project_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/TaskTemplateForProject/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time(self, *, task_id=None):
        """
        Get
        """
        path = f"/TaskTime"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_time(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskTime"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_task_time_count(self, *, task_id=None):
        """
        Get
        """
        path = f"/odata/TaskTime/$count"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time_query_get_time_id(self, time_id):
        """
        Get
        """
        path = f"/TaskTime/query/Get/{quote(str(time_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time_query_get_total_time_spent_task_id(self, task_id):
        """
        GetTotalTimeSpent
        """
        path = f"/TaskTime/query/GetTotalTimeSpent/{quote(str(task_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time_query_get_user_time_spent_task_id_user_id(self, task_id, user_id):
        """
        GetUserTimeSpent
        """
        path = f"/TaskTime/query/GetUserTimeSpent/{quote(str(task_id), safe="")}/{quote(str(user_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time_query_get_object_permissions_comment_id(self, comment_id, *, time_id=None):
        """
        GetObjectPermissions
        """
        path = f"/TaskTime/query/GetObjectPermissions/{quote(str(comment_id), safe="")}"
        query_params = {}
        if time_id is not None:
            query_params["timeId"] = time_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_task_time_query_get_type_permissions(self, *, task_id=None):
        """
        GetTypePermissions
        """
        path = f"/TaskTime/query/GetTypePermissions"
        query_params = {}
        if task_id is not None:
            query_params["taskId"] = task_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_time_command_create_for_date(self, *, body=None):
        """
        CreateForDate
        """
        path = f"/TaskTime/command/CreateForDate"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_time_command_create_for_date_range(self, *, body=None):
        """
        CreateForDateRange
        """
        path = f"/TaskTime/command/CreateForDateRange"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def patch_task_time_command_update_time_id(self, time_id, *, body=None):
        """
        Update
        """
        path = f"/TaskTime/command/Update/{quote(str(time_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        if body is not None:
            if request_headers is None:
                request_headers = {}
            request_headers.setdefault("Content-Type", "application/json;odata.metadata=minimal;odata.streaming=true")
            json_body = body
        return self._request(
            "PATCH" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def delete_task_time_command_delete_time_id(self, time_id):
        """
        Delete
        """
        path = f"/TaskTime/command/Delete/{quote(str(time_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "DELETE" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def post_task_time_command_restore_time_id(self, time_id):
        """
        Restore
        """
        path = f"/TaskTime/command/Restore/{quote(str(time_id), safe="")}"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "POST" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_user_group_in_project_group_membership(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/UserGroupInProjectGroupMembership"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_group_in_project_group_membership(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/UserGroupInProjectGroupMembership"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_group_in_project_group_membership_count(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/UserGroupInProjectGroupMembership/$count"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_user_group_in_project_membership(self, *, project_id=None):
        """
        Get
        """
        path = f"/UserGroupInProjectMembership"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_group_in_project_membership(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/UserGroupInProjectMembership"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_group_in_project_membership_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/UserGroupInProjectMembership/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_user_in_project_group_membership(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/UserInProjectGroupMembership"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_in_project_group_membership(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/UserInProjectGroupMembership"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_in_project_group_membership_count(self, *, project_group_id=None):
        """
        Get
        """
        path = f"/odata/UserInProjectGroupMembership/$count"
        query_params = {}
        if project_group_id is not None:
            query_params["projectGroupId"] = project_group_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_user_in_project_membership(self, *, project_id=None):
        """
        Get
        """
        path = f"/UserInProjectMembership"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_in_project_membership(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/UserInProjectMembership"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_user_in_project_membership_count(self, *, project_id=None):
        """
        Get
        """
        path = f"/odata/UserInProjectMembership/$count"
        query_params = {}
        if project_id is not None:
            query_params["projectId"] = project_id
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def get_weight_for_task_registry(self):
        """
        Get
        """
        path = f"/WeightForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_weight_for_task_registry(self):
        """
        Get
        """
        path = f"/odata/WeightForTaskRegistry"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )

    def odata_weight_for_task_registry_count(self):
        """
        Get
        """
        path = f"/odata/WeightForTaskRegistry/$count"
        query_params = None
        request_headers = {}
        request_headers = None
        json_body = None
        data = None
        return self._request(
            "GET" ,
            path,
            params=query_params,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )
