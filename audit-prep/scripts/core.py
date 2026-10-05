"""Shared helpers: config, errors, HTTP and output."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONFIG_NAME = "prep.yaml"


class PrepError(Exception):
    """A problem the user or agent has to fix. The message says what to do."""


def load_config(path: str | None) -> dict:
    """Read prep.yaml. Paths in it are relative to the file."""
    import yaml

    p = Path(path) if path else Path.cwd() / CONFIG_NAME
    if not p.exists():
        raise PrepError(f"No config at {p}. Copy assets/prep.example.yaml to {CONFIG_NAME} and fill it in.")
    cfg = yaml.safe_load(p.read_text()) or {}
    if cfg.get("platform") not in ("probo", "vanta", "drata", "folder"):
        raise PrepError(f"{p}: `platform` must be probo, vanta, drata or folder.")
    cfg.setdefault("options", {})
    cfg["_dir"] = str(p.parent.resolve())
    return cfg


def secret(env: str, command: str | None = None) -> str | None:
    """A credential from the environment, else from a command that prints it. Never printed."""
    if os.environ.get(env):
        return os.environ[env].strip()
    if command:
        out = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
        raise PrepError(f"token_command failed with exit code {out.returncode}. Run it yourself to see why.")
    return None


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value) -> datetime | None:
    if not value:
        return None
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def http_json(url: str, *, method: str = "GET", headers: dict | None = None, body=None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Accept": "application/json", **(headers or {})})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise PrepError(f"{method} {url} failed with HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise PrepError(f"{method} {url} failed: {e.reason}") from e


def multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    """Encode form fields and files. Returns (body, content type)."""
    import mimetypes

    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(value.encode() + b"\r\n")
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        filename = path.name.replace('"', "")
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode()
        )
        parts.append(path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_multipart(url: str, fields: dict[str, str], files: dict[str, Path], headers: dict, timeout: int = 300):
    body, ctype = multipart(fields, files)
    req = urllib.request.Request(url, data=body, method="POST", headers={**headers, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise PrepError(f"Upload to {url} failed with HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from e
