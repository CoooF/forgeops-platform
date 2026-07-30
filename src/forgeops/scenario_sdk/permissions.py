from __future__ import annotations

from forgeops.platform_contracts.package_permissions import (
    ALLOWED_PACKAGE_PERMISSIONS,
    FORBIDDEN_PACKAGE_CAPABILITIES,
)

# Backward-compatible names remain the Scenario SDK public truth.
ALLOWED_SCENARIO_PERMISSIONS = ALLOWED_PACKAGE_PERMISSIONS
FORBIDDEN_WORKER_CAPABILITIES = FORBIDDEN_PACKAGE_CAPABILITIES
