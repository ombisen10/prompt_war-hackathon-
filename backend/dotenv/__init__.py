"""Lightweight standard-library compatible dotenv loader."""
from __future__ import annotations
import os

def load_dotenv(dotenv_path: str | None = None, override: bool = False, **kwargs) -> bool:
    if dotenv_path is None:
        dotenv_path = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(dotenv_path):
            dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if override or k not in os.environ:
                            os.environ[k] = v
            return True
        except Exception:
            return False
    return False
