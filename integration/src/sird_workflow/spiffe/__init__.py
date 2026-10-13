"""Fail-closed SPIFFE identity and workload authorization primitives.

Isolated and unsupported: the project does not use SPIFFE/SPIRE. The
``sird_workflow`` root API does not export this package.

This module only validates identity values and credential metadata that a
caller has already obtained. It does not acquire SVIDs, validate trust
bundles, or integrate with SPIRE.
"""

from sird_workflow.spiffe._errors import (
    EmptyAuthorizationPolicyError as EmptyAuthorizationPolicyError,
)
from sird_workflow.spiffe._errors import (
    ExpiredCredentialError as ExpiredCredentialError,
)
from sird_workflow.spiffe._errors import (
    InvalidCredentialError as InvalidCredentialError,
)
from sird_workflow.spiffe._errors import (
    MalformedSpiffeIdError as MalformedSpiffeIdError,
)
from sird_workflow.spiffe._errors import (
    SpiffePolicyError as SpiffePolicyError,
)
from sird_workflow.spiffe._errors import (
    UnauthorizedWorkloadError as UnauthorizedWorkloadError,
)
from sird_workflow.spiffe._errors import (
    UnknownWorkloadRoleError as UnknownWorkloadRoleError,
)
from sird_workflow.spiffe._identity import (
    SpiffeAuthorizationPolicy as SpiffeAuthorizationPolicy,
)
from sird_workflow.spiffe._identity import SpiffeId as SpiffeId
from sird_workflow.spiffe._identity import (
    WorkloadCredential as WorkloadCredential,
)
from sird_workflow.spiffe._identity import (
    authorize_workload as authorize_workload,
)
from sird_workflow.spiffe._identity import (
    validate_credential as validate_credential,
)
from sird_workflow.spiffe._role import WorkloadRole as WorkloadRole
