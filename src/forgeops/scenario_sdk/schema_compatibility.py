from __future__ import annotations

from typing import Any


def find_breaking_schema_changes(
    previous: dict[str, Any], current: dict[str, Any], *, path: str = "$"
) -> tuple[str, ...]:
    """Conservative backward-compatibility check for JSON object schemas."""
    issues: list[str] = []
    previous_type = previous.get("type")
    current_type = current.get("type")
    if previous_type != current_type:
        issues.append(f"{path}: type changed from {previous_type!r} to {current_type!r}")
        return tuple(issues)

    if previous_type == "object":
        previous_properties = previous.get("properties", {})
        current_properties = current.get("properties", {})
        for name, previous_property in previous_properties.items():
            if name not in current_properties:
                issues.append(f"{path}.{name}: property removed")
                continue
            issues.extend(
                find_breaking_schema_changes(
                    previous_property, current_properties[name], path=f"{path}.{name}"
                )
            )
        previous_required = set(previous.get("required", []))
        current_required = set(current.get("required", []))
        new_required = current_required - previous_required
        for name in sorted(new_required):
            issues.append(f"{path}.{name}: newly required property")
    elif previous_type == "array":
        issues.extend(
            find_breaking_schema_changes(
                previous.get("items", {}), current.get("items", {}), path=f"{path}[]"
            )
        )

    previous_enum = set(previous.get("enum", []))
    current_enum = set(current.get("enum", []))
    removed_enum_values = previous_enum - current_enum
    if removed_enum_values:
        issues.append(f"{path}: enum values removed: {sorted(removed_enum_values)!r}")
    return tuple(issues)
