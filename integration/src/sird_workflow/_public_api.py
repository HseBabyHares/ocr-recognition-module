"""Consolidated public API for :mod:`sird_workflow`."""

from importlib import import_module as _import_module
from sys import modules as _modules

from sird_workflow import _public_api_artifacts as _artifacts
from sird_workflow import _public_api_dispatch as _dispatch
from sird_workflow import _public_api_transport as _transport
from sird_workflow import _public_api_workflow as _workflow

ArtifactCapability = _artifacts.ArtifactCapability
ArtifactCapabilitySigner = _artifacts.ArtifactCapabilitySigner
ArtifactCapabilityValidator = _artifacts.ArtifactCapabilityValidator
ArtifactChecksumError = _artifacts.ArtifactChecksumError
ArtifactDecodeError = _artifacts.ArtifactDecodeError
ArtifactDecoder = _artifacts.ArtifactDecoder
ArtifactPolicyError = _artifacts.ArtifactPolicyError
ArtifactReader = _artifacts.ArtifactReader
ArtifactReadError = _artifacts.ArtifactReadError
ArtifactReadPolicy = _artifacts.ArtifactReadPolicy
ArtifactRef = _artifacts.ArtifactRef
ArtifactSecurityError = _artifacts.ArtifactSecurityError
ArtifactSizeMismatchError = _artifacts.ArtifactSizeMismatchError
ArtifactSource = _artifacts.ArtifactSource
CapabilityClaimMismatchError = _artifacts.CapabilityClaimMismatchError
CapabilityExpiredError = _artifacts.CapabilityExpiredError
CapabilitySignatureError = _artifacts.CapabilitySignatureError
MalformedCapabilityError = _artifacts.MalformedCapabilityError

AttemptBudget = _artifacts.AttemptBudget
AttemptBudgetExhaustedError = _artifacts.AttemptBudgetExhaustedError
AttemptLease = _artifacts.AttemptLease
DuplicateTerminalTransitionError = _artifacts.DuplicateTerminalTransitionError
StaleAttemptLeaseError = _artifacts.StaleAttemptLeaseError

CancellationToken = _artifacts.CancellationToken
WorkflowConfig = _artifacts.WorkflowConfig

MessageAcknowledger = _artifacts.MessageAcknowledger
OffsetCommitter = _artifacts.OffsetCommitter
RabbitMQConsumerConfig = _artifacts.RabbitMQConsumerConfig
RabbitMQTaskConsumer = _artifacts.RabbitMQTaskConsumer
TaskConsumerDecision = _artifacts.TaskConsumerDecision
TaskConsumerMessage = _artifacts.TaskConsumerMessage

Base = _artifacts.Base
TaskAttemptRecord = _artifacts.TaskAttemptRecord
TaskDeadLetterOutbox = _artifacts.TaskDeadLetterOutbox
TaskOutbox = _artifacts.TaskOutbox
TaskRecord = _artifacts.TaskRecord
TaskResultOutbox = _artifacts.TaskResultOutbox
create_schema = _artifacts.create_schema
make_engine = _artifacts.make_engine

BrokerAcknowledgement = _workflow.BrokerAcknowledgement
DeadLetterEvent = _workflow.DeadLetterEvent
DeadLetterOutbox = _workflow.DeadLetterOutbox
DeadLetterPublisher = _workflow.DeadLetterPublisher
DeadLetterState = _workflow.DeadLetterState
PublicationNotAcknowledgedError = _workflow.PublicationNotAcknowledgedError

InvalidIdempotentReuseError = _workflow.InvalidIdempotentReuseError
PublicationFailureError = _workflow.PublicationFailureError
TaskNotFoundError = _workflow.TaskNotFoundError
UnauthenticatedCallerError = _workflow.UnauthenticatedCallerError
WorkflowError = _workflow.WorkflowError

InvalidTaskEventError = _workflow.InvalidTaskEventError

DEFAULT_RETENTION_SECONDS = _workflow.DEFAULT_RETENTION_SECONDS
SubmitRequest = _workflow.SubmitRequest
TaskResult = _workflow.TaskResult
TaskStatus = _workflow.TaskStatus
TaskSubmission = _workflow.TaskSubmission

OcrCallResult = _workflow.OcrCallResult
OcrClient = _workflow.OcrClient
OCR_DEADLINE_SECONDS = _dispatch.OCR_DEADLINE_SECONDS
OcrOutcome = _dispatch.OcrOutcome

DispatchReport = _dispatch.DispatchReport
OutboxDispatchReport = _dispatch.OutboxDispatchReport
TaskOutboxDispatcher = _dispatch.TaskOutboxDispatcher

ProcessService = _dispatch.ProcessService

ProcessDispatchReport = _dispatch.ProcessDispatchReport
ProcessOutboxDispatcher = _dispatch.ProcessOutboxDispatcher
ProcessOutboxDispatchReport = _dispatch.ProcessOutboxDispatchReport

ProcessOutcome = _dispatch.ProcessOutcome

PublisherConfirmationError = _transport.PublisherConfirmationError
RabbitMQDeadLetterPublisher = _transport.RabbitMQDeadLetterPublisher
RabbitMQProducerConfig = _transport.RabbitMQProducerConfig
RabbitMQTaskProducer = _transport.RabbitMQTaskProducer
TaskProducer = _transport.TaskProducer
UnroutableMessageError = _transport.UnroutableMessageError

WorkflowService = _transport.WorkflowService

EmptyAuthorizationPolicyError = _transport.EmptyAuthorizationPolicyError
ExpiredCredentialError = _transport.ExpiredCredentialError
InvalidCredentialError = _transport.InvalidCredentialError
MalformedSpiffeIdError = _transport.MalformedSpiffeIdError
SpiffeAuthorizationPolicy = _transport.SpiffeAuthorizationPolicy
SpiffeId = _transport.SpiffeId
SpiffePolicyError = _transport.SpiffePolicyError
UnauthorizedWorkloadError = _transport.UnauthorizedWorkloadError
UnknownWorkloadRoleError = _transport.UnknownWorkloadRoleError
WorkloadCredential = _transport.WorkloadCredential
WorkloadRole = _transport.WorkloadRole
authorize_workload = _transport.authorize_workload
validate_credential = _transport.validate_credential

TASK_EVENT_TYPE = _transport.TASK_EVENT_TYPE
TaskEvent = _transport.TaskEvent

DEAD_LETTER_EVENT_TYPE = _transport.DEAD_LETTER_EVENT_TYPE
RESULT_EVENT_TYPE = _transport.RESULT_EVENT_TYPE


class _PublicApiLookup:
    def __init__(self) -> None:
        self._package_name = __name__.partition(".")[0]
        self._api_name = __name__

    def __call__(self, name: str) -> object:
        if name.startswith("__"):
            raise AttributeError(name)
        api_module = _modules[self._api_name]
        public_value = api_module.__dict__.get(name)
        if public_value is not None:
            return public_value
        try:
            return _import_module(f"{self._package_name}.{name}")
        except ModuleNotFoundError as error:
            raise AttributeError(name) from error


__getattr__ = _PublicApiLookup()
