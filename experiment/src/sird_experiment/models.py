"""Immutable contracts for isolated OCR experiments."""

from sird_experiment import _model_enums, _model_plan, _model_records

ExperimentMode = _model_enums.ExperimentMode
ExperimentStatus = _model_enums.ExperimentStatus
SampleStatus = _model_enums.SampleStatus

ExperimentPlan = _model_plan.ExperimentPlan
ExperimentVariant = _model_plan.ExperimentVariant

EvaluationRecord = _model_records.EvaluationRecord
PredictionRecord = _model_records.PredictionRecord
SampleExecutionRecord = _model_records.SampleExecutionRecord
SelectionDecision = _model_records.SelectionDecision
