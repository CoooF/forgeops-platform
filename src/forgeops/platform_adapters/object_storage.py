from __future__ import annotations

import hashlib
import os
from pathlib import Path


class ContentAddressedFileStore:
    """Local synthetic object-store replacement with immutable content addressing."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        target = self._root / "sha256" / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != content:
                raise RuntimeError("content-address collision")
            return f"file+sha256://{digest}"
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.chmod(temporary, 0o440)
        temporary.replace(target)
        return f"file+sha256://{digest}"

    def get(self, reference: str) -> bytes:
        digest = reference.removeprefix("file+sha256://")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("invalid content reference")
        return (self._root / "sha256" / digest[:2] / digest).read_bytes()
