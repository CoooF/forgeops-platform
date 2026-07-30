from __future__ import annotations

from pathlib import Path

from forgeops.platform_adapters.object_storage import ContentAddressedFileStore


def test_content_addressed_storage_is_idempotent_and_readable(tmp_path: Path) -> None:
    store = ContentAddressedFileStore(tmp_path)
    first = store.put(b"synthetic evidence")
    second = store.put(b"synthetic evidence")
    assert first == second
    assert store.get(first) == b"synthetic evidence"
