from __future__ import annotations

from typing import Protocol

from forgeops.platform_contracts.domain import Environment
from forgeops.platform_core.identity_access.entities import AuthenticatedPrincipal


class AuthPort(Protocol):
    def authenticate(self, credential: str | None) -> AuthenticatedPrincipal | None: ...


class LocalSyntheticAuthAdapter:
    """Maps a local-only header value to a subject reference; grants no permissions."""

    def authenticate(self, credential: str | None) -> AuthenticatedPrincipal | None:
        if credential is None or not credential.strip() or len(credential) > 256:
            return None
        return AuthenticatedPrincipal(subject_ref=credential.strip())


class UnavailableAuthAdapter:
    """Fails closed where no approved enterprise identity adapter is connected."""

    def authenticate(self, credential: str | None) -> None:
        del credential
        return None


def auth_adapter_for_environment(environment: Environment) -> AuthPort:
    if environment in {Environment.DEV, Environment.TEST}:
        return LocalSyntheticAuthAdapter()
    return UnavailableAuthAdapter()
