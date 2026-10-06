"""Transport, identity, and terminal writer API exports."""

from sird_workflow import _producer_support, _spiffe_errors
from sird_workflow import producer as _producer
from sird_workflow import service as _service
from sird_workflow import spiffe as _spiffe
from sird_workflow import task_event as _task_event
from sird_workflow import task_terminal_writer as _task_terminal_writer

PublisherConfirmationError = _producer_support.PublisherConfirmationError
UnroutableMessageError = _producer_support.UnroutableMessageError
EmptyAuthorizationPolicyError = _spiffe_errors.EmptyAuthorizationPolicyError
ExpiredCredentialError = _spiffe_errors.ExpiredCredentialError
InvalidCredentialError = _spiffe_errors.InvalidCredentialError
MalformedSpiffeIdError = _spiffe_errors.MalformedSpiffeIdError
SpiffePolicyError = _spiffe_errors.SpiffePolicyError
UnauthorizedWorkloadError = _spiffe_errors.UnauthorizedWorkloadError
UnknownWorkloadRoleError = _spiffe_errors.UnknownWorkloadRoleError

RabbitMQDeadLetterPublisher = _producer.RabbitMQDeadLetterPublisher
RabbitMQProducerConfig = _producer.RabbitMQProducerConfig
RabbitMQTaskProducer = _producer.RabbitMQTaskProducer
TaskProducer = _producer.TaskProducer

WorkflowService = _service.WorkflowService

SpiffeAuthorizationPolicy = _spiffe.SpiffeAuthorizationPolicy
SpiffeId = _spiffe.SpiffeId
WorkloadCredential = _spiffe.WorkloadCredential
WorkloadRole = _spiffe.WorkloadRole
authorize_workload = _spiffe.authorize_workload
validate_credential = _spiffe.validate_credential

TASK_EVENT_TYPE = _task_event.TASK_EVENT_TYPE
TaskEvent = _task_event.TaskEvent

DEAD_LETTER_EVENT_TYPE = _task_terminal_writer.DEAD_LETTER_EVENT_TYPE
RESULT_EVENT_TYPE = _task_terminal_writer.RESULT_EVENT_TYPE
