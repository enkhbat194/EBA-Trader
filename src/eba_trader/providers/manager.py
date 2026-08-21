from __future__ import annotations

from collections.abc import Callable

from .base import (
    ConnectionProfile,
    ConnectionTestResult,
    CredentialEnvelope,
    ProviderAdapter,
    ProviderKind,
)

ProviderFactory = Callable[[ConnectionProfile, CredentialEnvelope], ProviderAdapter]


class ConnectionManager:
    """Registry and lifecycle boundary for exchange/broker adapters."""

    def __init__(self) -> None:
        self._factories: dict[ProviderKind, ProviderFactory] = {}
        self._profiles: dict[str, ConnectionProfile] = {}

    def register(self, kind: ProviderKind, factory: ProviderFactory) -> None:
        if kind in self._factories:
            raise ValueError(f"provider already registered: {kind}")
        self._factories[kind] = factory

    def upsert_profile(self, profile: ConnectionProfile) -> None:
        self._profiles[profile.connection_id] = profile

    def get_profile(self, connection_id: str) -> ConnectionProfile:
        try:
            return self._profiles[connection_id]
        except KeyError as exc:
            raise KeyError(f"unknown connection: {connection_id}") from exc

    def list_profiles(self) -> tuple[ConnectionProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def build_adapter(
        self,
        connection_id: str,
        credentials: CredentialEnvelope,
    ) -> ProviderAdapter:
        profile = self.get_profile(connection_id)
        try:
            factory = self._factories[profile.provider]
        except KeyError as exc:
            raise RuntimeError(f"provider not registered: {profile.provider}") from exc
        return factory(profile, credentials)

    def test_connection(
        self,
        connection_id: str,
        credentials: CredentialEnvelope,
    ) -> ConnectionTestResult:
        return self.build_adapter(connection_id, credentials).test_connection()
