"""Pure-Python standard-library FastAPI compatible framework."""
from __future__ import annotations
import asyncio
import inspect
import json
import re
from typing import Any, Callable, Optional
from pydantic import BaseModel, ValidationError


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class Request:
    def __init__(self, method: str, path: str, headers: dict[str, str], body: bytes = b"", query_params: dict[str, str] = None):
        self.method = method
        self.path = path
        self.headers = headers
        self._body = body
        self.query_params = query_params or {}

    async def body(self) -> bytes:
        return self._body

    async def json(self) -> Any:
        if not self._body:
            return {}
        return json.loads(self._body.decode("utf-8"))


class Route:
    def __init__(self, method: str, path_pattern: str, handler: Callable, response_model: Any = None):
        self.method = method.upper()
        self.path_pattern = path_pattern
        self.handler = handler
        self.response_model = response_model
        # Convert path pattern (e.g. /api/incidents/{incident_id}) to regex
        regex_pattern = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"(?P<\1>[^/]+)", path_pattern)
        self.regex = re.compile(f"^{regex_pattern}$")

    def match(self, method: str, path: str) -> Optional[dict[str, str]]:
        if self.method != method.upper():
            return None
        m = self.regex.match(path)
        if m:
            return m.groupdict()
        return None


class FastAPI:
    def __init__(self, title: str = "FastAPI", description: str = "", version: str = "0.1.0", lifespan: Any = None):
        self.title = title
        self.description = description
        self.version = version
        self.lifespan = lifespan
        self.routes: list[Route] = []
        self.exception_handlers: dict[Any, Callable] = {}
        self.cors_origins: list[str] = ["*"]

    def add_middleware(self, middleware_class: Any, **kwargs: Any):
        if "allow_origins" in kwargs:
            self.cors_origins = kwargs["allow_origins"]

    def exception_handler(self, exc_or_status: Any):
        def decorator(fn: Callable):
            self.exception_handlers[exc_or_status] = fn
            return fn
        return decorator

    def get(self, path: str, response_model: Any = None):
        def decorator(fn: Callable):
            self.routes.append(Route("GET", path, fn, response_model))
            return fn
        return decorator

    def post(self, path: str, response_model: Any = None):
        def decorator(fn: Callable):
            self.routes.append(Route("POST", path, fn, response_model))
            return fn
        return decorator

    def put(self, path: str, response_model: Any = None):
        def decorator(fn: Callable):
            self.routes.append(Route("PUT", path, fn, response_model))
            return fn
        return decorator

    def delete(self, path: str, response_model: Any = None):
        def decorator(fn: Callable):
            self.routes.append(Route("DELETE", path, fn, response_model))
            return fn
        return decorator

    async def dispatch(self, method: str, path: str, body: bytes = b"", headers: dict[str, str] = None) -> tuple[int, dict[str, str], bytes]:
        headers = headers or {}
        req_origin = headers.get("origin") or headers.get("Origin") or ""
        matched_origin = "*"
        if self.cors_origins:
            if "*" in self.cors_origins:
                matched_origin = req_origin if req_origin else "*"
            elif req_origin and req_origin in self.cors_origins:
                matched_origin = req_origin
            else:
                matched_origin = self.cors_origins[0]

        # Preflight CORS
        if method.upper() == "OPTIONS":
            cors_headers = {
                "Access-Control-Allow-Origin": matched_origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Credentials": "true",
            }
            return 200, cors_headers, b""

        # Find route
        matched_route = None
        path_params = {}
        for r in self.routes:
            m = r.match(method, path)
            if m is not None:
                matched_route = r
                path_params = m
                break

        cors_headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": matched_origin,
            "Access-Control-Allow-Credentials": "true",
        }

        if matched_route is None:
            return 404, cors_headers, json.dumps({"detail": "Not Found"}).encode("utf-8")

        req_obj = Request(method=method, path=path, headers=headers, body=body)

        try:
            # Build arguments for handler
            sig = inspect.signature(matched_route.handler)
            args_to_pass = {}
            body_json = None
            if body:
                try:
                    body_json = json.loads(body.decode("utf-8"))
                except Exception:
                    body_json = None

            hints = {}
            try:
                import typing
                hints = typing.get_type_hints(matched_route.handler)
            except Exception:
                hints = {}

            for param_name, param in sig.parameters.items():
                annotation = hints.get(param_name, param.annotation)
                if isinstance(annotation, str):
                    annotation = getattr(matched_route.handler, "__globals__", {}).get(annotation, annotation)

                if param_name in path_params:
                    args_to_pass[param_name] = path_params[param_name]
                elif annotation is Request or param_name == "request":
                    args_to_pass[param_name] = req_obj
                elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    if body_json is None:
                        raise HTTPException(422, "Missing request body")
                    try:
                        args_to_pass[param_name] = annotation.model_validate(body_json)
                    except ValidationError as ve:
                        raise HTTPException(422, {"detail": ve.errors()})
                    except Exception as ve:
                        raise HTTPException(422, str(ve))
                elif body_json is not None and isinstance(body_json, dict) and param_name in body_json:
                    args_to_pass[param_name] = body_json[param_name]
                elif param.default is not inspect.Parameter.empty:
                    args_to_pass[param_name] = param.default
                else:
                    args_to_pass[param_name] = None

            # Execute handler
            res = matched_route.handler(**args_to_pass)
            if inspect.iscoroutine(res):
                res = await res

            # Serialize output
            if isinstance(res, BaseModel):
                data = res.model_dump()
            elif isinstance(res, list):
                data = [item.model_dump() if isinstance(item, BaseModel) else item for item in res]
            elif isinstance(res, dict):
                data = {k: (v.model_dump() if isinstance(v, BaseModel) else v) for k, v in res.items()}
            else:
                data = res

            return 200, cors_headers, json.dumps(data, default=str).encode("utf-8")

        except HTTPException as he:
            if he.status_code in self.exception_handlers:
                err_res = self.exception_handlers[he.status_code](req_obj, he)
                if inspect.iscoroutine(err_res):
                    err_res = await err_res
                return he.status_code, cors_headers, json.dumps(err_res, default=str).encode("utf-8")
            return he.status_code, cors_headers, json.dumps({"detail": he.detail}).encode("utf-8")
        except ValidationError as ve:
            if 422 in self.exception_handlers:
                err_res = self.exception_handlers[422](req_obj, ve)
                if inspect.iscoroutine(err_res):
                    err_res = await err_res
                return 422, cors_headers, json.dumps(err_res, default=str).encode("utf-8")
            return 422, cors_headers, json.dumps({"detail": ve.errors()}).encode("utf-8")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return 500, cors_headers, json.dumps({"detail": str(exc)}).encode("utf-8")

    # WSGI support
    def __call__(self, environ: dict, start_response: Callable) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            content_length = 0
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""

        headers = {}
        for k, v in environ.items():
            if k.startswith("HTTP_"):
                headers[k[5:].lower().replace("_", "-")] = v
            elif k in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[k.lower().replace("_", "-")] = v

        loop = asyncio.new_event_loop()
        try:
            status_code, resp_headers, resp_body = loop.run_until_complete(
                self.dispatch(method, path, body, headers)
            )
        finally:
            loop.close()

        status_str = f"{status_code} " + {
            200: "OK", 201: "Created", 204: "No Content",
            400: "Bad Request", 403: "Forbidden", 404: "Not Found",
            422: "Unprocessable Entity", 500: "Internal Server Error",
        }.get(status_code, "OK")

        start_response(status_str, list(resp_headers.items()))
        return [resp_body]
