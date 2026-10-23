"""CLI entrypoint for uvicorn runner."""
import sys
from uvicorn import run

if __name__ == "__main__":
    app_str = "app.main:app"
    port = 8000
    host = "127.0.0.1"

    args = sys.argv[1:]
    if args and not args[0].startswith("-"):
        app_str = args[0]
        args = args[1:]

    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i+1])
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i+1]
            i += 2
        else:
            i += 1

    run(app_str, host=host, port=port)
