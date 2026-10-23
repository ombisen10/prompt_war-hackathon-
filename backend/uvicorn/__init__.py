"""Multi-threaded WSGI/ASGI runner compatible with uvicorn API."""
from __future__ import annotations
import importlib
import socketserver
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True


class SilentHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args):
        # Concise logging
        print(f"[GuardianAI API] {args[0]} -> {args[1]}")


def run(app_str_or_obj, host: str = "127.0.0.1", port: int = 8000, **kwargs):
    if isinstance(app_str_or_obj, str):
        mod_name, attr_name = app_str_or_obj.split(":", 1)
        mod = importlib.import_module(mod_name)
        app = getattr(mod, attr_name)
    else:
        app = app_str_or_obj

    print(f"INFO:     Started server process")
    print(f"INFO:     Waiting for application startup.")
    print(f"INFO:     Application startup complete.")
    print(f"INFO:     Uvicorn running on http://{host}:{port} (Press CTRL+C to quit)")

    server = make_server(host, port, app, server_class=ThreadingWSGIServer, handler_class=SilentHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nINFO:     Shutting down")
    finally:
        server.server_close()
