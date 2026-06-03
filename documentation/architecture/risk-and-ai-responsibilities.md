# Risk and AI Responsibilities

This document explains responsibility boundaries between deterministic risk logic and AI narrative generation.

## 1) Responsibility Split

## 1.1 Deterministic risk responsibilities

Deterministic risk belongs to the risk layer:

- `services/risk/driver_risk_engine.py::DriverRiskEngine`
- `services/risk/engine.py::RiskEngine`

Key responsibilities:

- deterministic feature-driven assessment,
- deterministic risk level and confidence outputs,
- deterministic intervention and explainability structures,
- deterministic concern ranking.

`DriverRiskEngine` is a compatibility facade that maps legacy API expectations to v2 deterministic outputs.

```python
class DriverRiskEngine:
    RISK_MODEL_VERSION = RiskEngine.RISK_MODEL_VERSION

assessment = RiskEngine.build_assessment(normalized_data)
```

## 1.2 AI narrative responsibilities

Narrative generation belongs to:

- `services/ai_summary.py::generate_driver_behaviour_aggregated_summary`
- `services/ai_summary.py::generate_fleet_summary_text`

Key responsibilities:

- convert deterministic/normalized input into plain-language summaries,
- sanitize prompt payloads before model calls,
- provide deterministic fallback text on invalid/empty payloads or upstream failures.

The AI layer is a communication layer, not the source of deterministic risk truth.

## 2) Driver Behaviour Data Ownership

Driver flow ownership is intentionally split:

1. Pipeline builds deterministic analysis payload (`services/summary_pipeline.py::_aggregate_driver_behaviour_payload`).
2. Risk layer computes deterministic risk structures used in that payload.
3. AI layer receives sanitized payload and writes narrative text.

This keeps risk semantics auditable in Python code while keeping summary prose adaptable.

## 3) Fleet Flow Ownership

Fleet flow currently builds deterministic fleet analysis heuristics in pipeline and asks AI to produce narrative summary text.

- Fleet does not use `RiskEngine` dimensions directly in current endpoint orchestration.
- Fleet AI prompt remains bounded by sanitized normalized data.

## 4) Guardrails and Safety Behaviors

Guardrails are enforced by implementation + tests:

- Prompt sanitization prevents arbitrary fields from entering model prompts.
- Tests assert guardrail instruction fragments and sanitized prompt content.
- Error and empty-data fallbacks return deterministic safe responses.

See `tests/services/test_ai_summary.py` for these guarantees.

## 5) Risk Engine Deep Dive

For final v2 dimension composition semantics, use the authoritative risk-engine document:

- `documentation/architecture/risk-engine.md`

This document links to that source and intentionally does not duplicate all decision-contract detail.

## 6) Why This Boundary Matters

- Deterministic risk remains testable and reproducible.
- AI output variability is constrained to wording, not core scoring logic.
- On-call/debugging is simpler because deterministic analysis payloads are inspectable independent of AI behavior.