"""Explicit records exchanged by stateless OCR stages."""

from sird_recognition.contracts import execution as _execution
from sird_recognition.contracts import field_results as _field_results
from sird_recognition.contracts import form_resolution as _form_resolution
from sird_recognition.contracts import prepared as _prepared

ExecutionResult = _execution.ExecutionResult
FieldResult = _field_results.FieldResult
FieldStatus = _field_results.FieldStatus
AmbiguousForm = _form_resolution.AmbiguousForm
FormResolutionDecision = _form_resolution.FormResolutionDecision
ResolvedForm = _form_resolution.ResolvedForm
UnresolvedForm = _form_resolution.UnresolvedForm
UnsupportedForm = _form_resolution.UnsupportedForm
ExecutionSpec = _prepared.ExecutionSpec
PreparedDocument = _prepared.PreparedDocument
PreparedPage = _prepared.PreparedPage
ProbeResult = _prepared.ProbeResult
StageContext = _prepared.StageContext
