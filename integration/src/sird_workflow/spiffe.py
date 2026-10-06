"""Fail-closed SPIFFE identity and workload authorization primitives.

This module only validates identity values and credential metadata that a
caller has already obtained. It does not acquire SVIDs, validate trust
bundles, or integrate with SPIRE.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import cast

from sird_workflow import (
    _spiffe_errors as errors_module,
)
from sird_workflow import (
    _spiffe_helpers as helpers_module,
)
from sird_workflow._spiffe_role import WorkloadRole

SpiffePolicyError = errors_module.SpiffePolicyError
MalformedSpiffeIdError = errors_module.MalformedSpiffeIdError
EmptyAuthorizationPolicyError = errors_module.EmptyAuthorizationPolicyError
UnknownWorkloadRoleError = errors_module.UnknownWorkloadRoleError
InvalidCredentialError = errors_module.InvalidCredentialError
ExpiredCredentialError = errors_module.ExpiredCredentialError
UnauthorizedWorkloadError = errors_module.UnauthorizedWorkloadError


@dataclass(frozen=True, slots=True, init=False)
class SpiffeId:
    """A parsed SPIFFE ID whose original string is retained exactly."""

    identifier: str
    trust_domain: str
    path: str

    def __init__(
        self, identifier: str | None = None, **options: object
    ) -> None:
        if identifier is None and "value" in options:
            candidate = options.pop("value")
            identifier = cast(str, candidate)
        if options:
            raise TypeError("unexpected SPIFFE identity arguments")
        identifier_value = cast(str, identifier)
        parsed = helpers_module.parse_spiffe_id(identifier_value)
        object.__setattr__(self, "identifier", identifier_value)
        object.__setattr__(self, "trust_domain", parsed[0])
        object.__setattr__(self, "path", parsed[1])

    @property
    def as_text(self) -> str:
        """Return the exact source value."""
        return self.identifier

    def __str__(self) -> str:
        return self.identifier

    @classmethod
    def parse(cls, identifier: str) -> SpiffeId:
        """Parse a SPIFFE ID and retain its exact source value."""
        return cls(identifier)

    @property
    def id(self) -> str:
        """Return the exact SPIFFE ID string."""
        return self.identifier


type.__setattr__(SpiffeId, "value", property(SpiffeId.as_text.fget))


@dataclass(frozen=True, slots=True, init=False)
class SpiffeAuthorizationPolicy:
    """Exact SPIFFE ID to role mappings for one authorization boundary."""

    allowed_roles: Mapping[str, WorkloadRole]

    def __init__(
        self,
        allowed_roles: (
            Mapping[str | SpiffeId, WorkloadRole | str] | None
        ) = None,
        *,
        identity_roles: (
            Mapping[str | SpiffeId, WorkloadRole | str] | None
        ) = None,
        allowed_identities: (
            Mapping[str | SpiffeId, WorkloadRole | str] | None
        ) = None,
    ) -> None:
        supplied = [
            mapping
            for mapping in (allowed_roles, identity_roles, allowed_identities)
            if mapping is not None
        ]
        if len(supplied) != 1 or not supplied[0]:
            raise errors_module.EmptyAuthorizationPolicyError(
                "authorization policy must contain at least one identity"
            )

        normalized: dict[str, WorkloadRole] = {}
        for identity, role in supplied[0].items():
            parsed_identity = helpers_module.coerce_spiffe_id(identity)
            normalized[parsed_identity.value] = helpers_module.coerce_role(
                role
            )
        if not normalized:
            raise errors_module.EmptyAuthorizationPolicyError(
                "authorization policy must contain at least one identity"
            )
        object.__setattr__(self, "allowed_roles", MappingProxyType(normalized))

    def role_for(self, identity: SpiffeId | str) -> WorkloadRole:
        """Return the configured role for an exact identity."""
        parsed_identity = helpers_module.coerce_spiffe_id(identity)
        try:
            return self.allowed_roles[parsed_identity.value]
        except KeyError as error:
            raise errors_module.UnauthorizedWorkloadError(
                "workload identity is not authorized"
            ) from error

    def authorize_workload(
        self,
        credential: WorkloadCredential,
        role: WorkloadRole | str,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Validate a credential and authorize its exact ID for ``role``."""
        return authorize_workload(self, credential, role, now=now)


@dataclass(frozen=True, slots=True)
class WorkloadCredential:
    """Identity and time metadata obtained from an external workload system.

    The object deliberately contains no CA or trust-bundle decision. A caller
    must provide a credential with an exact SPIFFE ID; authorization never
    succeeds from CA validation alone.
    """

    spiffe_id: SpiffeId | str
    expires_at: datetime
    issued_at: datetime | None = None
    renewed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "spiffe_id", helpers_module.coerce_spiffe_id(self.spiffe_id)
        )
        helpers_module.validate_timestamp(self.expires_at, "credential expiry")
        if self.issued_at is not None:
            helpers_module.validate_timestamp(
                self.issued_at, "credential issue"
            )
        if self.renewed_at is not None:
            helpers_module.validate_timestamp(
                self.renewed_at, "credential renewal"
            )
        if (
            self.issued_at is not None
            and self.renewed_at is not None
            and self.renewed_at < self.issued_at
        ):
            raise errors_module.InvalidCredentialError(
                "credential renewal precedes credential issue"
            )


class _CredentialValidator:
    @classmethod
    def require_credential(cls, credential: object) -> WorkloadCredential:
        if not isinstance(credential, WorkloadCredential):
            raise errors_module.InvalidCredentialError(
                "credential has an invalid type"
            )
        return credential

    @classmethod
    def require_identity(
        cls,
        credential: WorkloadCredential,
        identity: SpiffeId,
        expected_id: SpiffeId | str | None,
    ) -> None:
        if expected_id is not None:
            expected_identity = helpers_module.coerce_spiffe_id(expected_id)
            if identity != expected_identity:
                raise errors_module.InvalidCredentialError(
                    "credential identity does not match"
                )

    @classmethod
    def require_time_bounds(
        cls, credential: WorkloadCredential, current: datetime
    ) -> None:
        if credential.issued_at is not None and credential.issued_at > current:
            raise errors_module.InvalidCredentialError(
                "credential is not valid yet"
            )
        if (
            credential.renewed_at is not None
            and credential.renewed_at > current
        ):
            raise errors_module.InvalidCredentialError(
                "credential renewal is not valid yet"
            )
        if credential.expires_at <= current:
            raise errors_module.ExpiredCredentialError(
                "credential has expired"
            )


def validate_credential(
    credential: WorkloadCredential,
    *,
    now: datetime | None = None,
    expected_id: SpiffeId | str | None = None,
) -> bool:
    """Validate identity and expiry/renewal metadata, failing closed."""
    checked = _CredentialValidator.require_credential(credential)
    current = helpers_module.coerce_now(now)
    identity = helpers_module.coerce_spiffe_id(checked.spiffe_id)
    _CredentialValidator.require_identity(checked, identity, expected_id)
    _CredentialValidator.require_time_bounds(checked, current)
    return True


def authorize_workload(
    policy: SpiffeAuthorizationPolicy,
    credential: WorkloadCredential,
    role: WorkloadRole | str,
    *,
    now: datetime | None = None,
) -> bool:
    """Authorize a valid credential against an exact ID-to-role policy."""
    if not isinstance(policy, SpiffeAuthorizationPolicy):
        raise errors_module.UnauthorizedWorkloadError(
            "authorization policy has an invalid type"
        )
    validate_credential(credential, now=now)
    requested_role = helpers_module.coerce_role(role)
    configured_role = policy.role_for(credential.spiffe_id)
    if configured_role != requested_role:
        raise errors_module.UnauthorizedWorkloadError(
            "workload role is not authorized"
        )
    return True
