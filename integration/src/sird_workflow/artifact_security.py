"""Signed artifact capabilities and fail-closed decoder input guards.

The signer uses a versioned local HMAC-SHA256 envelope. Production key
storage, rotation, and identity selection remain external to this package.
Capabilities contain only SIRD-owned opaque object references; they never carry
URLs, filesystem paths, or document bytes.
"""

from sird_workflow._artifact_capability_errors import (
    ArtifactSecurityError,
    CapabilityClaimMismatchError,
    CapabilityExpiredError,
    CapabilitySignatureError,
    MalformedCapabilityError,
)
from sird_workflow._artifact_models import ArtifactCapability, ArtifactRef
from sird_workflow._artifact_read_errors import (
    ArtifactChecksumError,
    ArtifactDecodeError,
    ArtifactPolicyError,
    ArtifactReadError,
    ArtifactSizeMismatchError,
)
from sird_workflow._artifact_reader import (
    ArtifactDecoder,
    ArtifactReader,
    ArtifactReadPolicy,
    ArtifactSource,
)
from sird_workflow._artifact_signing import (
    ArtifactCapabilitySigner,
    ArtifactCapabilityValidator,
)
from sird_workflow.exceptions import WorkflowError

_PUBLIC_SYMBOLS = (
    ArtifactSecurityError,
    WorkflowError,
    MalformedCapabilityError,
    CapabilitySignatureError,
    CapabilityClaimMismatchError,
    CapabilityExpiredError,
    ArtifactCapability,
    ArtifactRef,
    ArtifactReadError,
    ArtifactPolicyError,
    ArtifactSizeMismatchError,
    ArtifactChecksumError,
    ArtifactDecodeError,
    ArtifactSource,
    ArtifactDecoder,
    ArtifactReadPolicy,
    ArtifactReader,
    ArtifactCapabilitySigner,
    ArtifactCapabilityValidator,
)
