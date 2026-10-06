"""Request validation and protobuf-to-domain translation helpers."""

from __future__ import annotations

from sird_recognition import _grpc_adapter_contract as _contract
from sird_recognition import _runtime_models
from sird_recognition._grpc_adapter_limits import map_limits
from sird_recognition._proto.sird.ocr.v1 import recognize_pb2
from sird_recognition.contracts.stages import StageContext


def _required_string(text: str, field_name: str) -> str:
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _reject_unknown(request: recognize_pb2.RecognizeRequest) -> None:
    known_request = recognize_pb2.RecognizeRequest()
    known_request.CopyFrom(request)
    known_request.DiscardUnknownFields()
    if known_request.SerializeToString(
        deterministic=True,
    ) != request.SerializeToString(deterministic=True):
        raise ValueError("unknown protobuf fields are not allowed")


def _read_identity(
    request: recognize_pb2.RecognizeRequest,
) -> tuple[str, str, str, str]:
    contract_version = _required_string(
        request.contract_version,
        "contract_version",
    )
    if contract_version != _contract.CONTRACT_VERSION:
        raise ValueError(
            f"contract_version must be {_contract.CONTRACT_VERSION}",
        )
    return (
        _required_string(request.task_id, "task_id"),
        _required_string(request.request_id, "request_id"),
        _required_string(request.attempt_id, "attempt_id"),
        contract_version,
    )


def _read_artifact(
    request: recognize_pb2.RecognizeRequest,
    identity: tuple[str, str, str, str],
) -> str:
    if not request.HasField("artifact_ref"):
        raise ValueError("artifact_ref is required")
    artifact = request.artifact_ref
    capability = _required_string(
        artifact.capability,
        "artifact_ref.capability",
    )
    task_id, request_id, _, _ = identity
    if artifact.task_id and artifact.task_id != task_id:
        raise ValueError(
            "artifact_ref.task_id does not match request identity"
        )
    if artifact.request_id and artifact.request_id != request_id:
        raise ValueError(
            "artifact_ref.request_id does not match request identity"
        )
    return capability


def _read_policy(
    request: recognize_pb2.RecognizeRequest,
) -> tuple[str, dict[str, int | float]]:
    if not request.HasField("processing_policy"):
        raise ValueError("processing_policy is required")
    policy = request.processing_policy
    policy_ref = _required_string(
        policy.input_policy_id,
        "processing_policy.input_policy_id",
    )
    required_fields = (
        (policy.input_policy_version, "input_policy_version"),
        (policy.classifier_policy_id, "classifier_policy_id"),
        (policy.classifier_policy_version, "classifier_policy_version"),
    )
    for field_text, field_name in required_fields:
        _required_string(field_text, f"processing_policy.{field_name}")
    if not policy.HasField("limits"):
        raise ValueError("processing_policy.limits is required")
    return policy_ref, map_limits(policy.limits)


def _build_requests(
    identity: tuple[str, str, str, str],
    capability: str,
    policy_ref: str,
    limits: dict[str, int | float],
) -> tuple[_runtime_models.RecognizeRequest, StageContext]:
    domain_request = _runtime_models.RecognizeRequest(
        task_id=identity[0],
        request_id=identity[1],
        artifact_capability=capability,
        limits=limits,
        policy_ref=policy_ref,
    )
    stage_context = StageContext(
        contract_version=identity[3],
        request_id=identity[1],
        attempt_id=identity[2],
        artifact_capability=capability,
        limits=limits,
        policy_ref=policy_ref,
    )
    return domain_request, stage_context


def parse_request(
    request: recognize_pb2.RecognizeRequest,
) -> tuple[_runtime_models.RecognizeRequest, StageContext]:
    _reject_unknown(request)
    identity = _read_identity(request)
    capability = _read_artifact(request, identity)
    policy_ref, limits = _read_policy(request)
    return _build_requests(identity, capability, policy_ref, limits)
