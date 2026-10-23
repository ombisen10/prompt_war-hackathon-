"""FastAPI TestClient compatible implementation."""
from __future__ import annotations
import asyncio
import json
from typing import Any, Optional


class Response:
    def __init__(self, status_code: int, headers: dict[str, str], content: bytes):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.text = content.decode("utf-8")

    def json(self) -> Any:
        if not self.content:
            return None
        return json.loads(self.text)


class TestClient:
    __test__ = False

    def __init__(self, app: Any):
        self.app = app

    def _request(self, method: str, url: str, json_data: Any = None, headers: Optional[dict[str, str]] = None) -> Response:
        body = b""
        req_headers = dict(headers or {})
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req_headers["content-type"] = "application/json"

        # Extract path without domain if full url provided
        path = url
        if "://" in url:
            path = "/" + url.split("://", 1)[1].split("/", 1)[1] if "/" in url.split("://", 1)[1] else "/"

        loop = asyncio.new_event_loop()
        try:
            status_code, resp_headers, resp_body = loop.run_until_complete(
                self.app.dispatch(method, path, body, req_headers)
            )
        finally:
            loop.close()

        return Response(status_code, resp_headers, resp_body)

    def get(self, url: str, headers: Optional[dict[str, str]] = None) -> Response:
        return self._request("GET", url, headers=headers)

    def post(self, url: str, json: Any = None, headers: Optional[dict[str, str]] = None) -> Response:
        return self._request("POST", url, json_data=json, headers=headers)

    def put(self, url: str, json: Any = None, headers: Optional[dict[str, str]] = None) -> Response:
        return self._request("PUT", url, json_data=json, headers=headers)

    def delete(self, url: str, headers: Optional[dict[str, str]] = None) -> Response:
        return self._request("DELETE", url, headers=headers)
