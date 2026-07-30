from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel


def canonical_value(value: Any) -> Any:
    """Return the FDS canonical JSON value; arrays are unordered contract sets."""
    if isinstance(value, BaseModel):
        value = value.model_dump(by_alias=True, mode="json", exclude_none=False)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [canonical_value(item) for item in value]
        return sorted(
            items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
        )
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"
