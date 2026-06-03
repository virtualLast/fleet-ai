# Testing and Quality Rails

This document maps architecture expectations to tests that enforce them.

## 1) API Contract Rails

Test module: `tests/api/test_api.py`

Protected behaviors:

- endpoint wiring for both active routes,
- response contract integrity for successful flows,
- validation failures returning `422` when required request fields are missing,
- runtime failure translation to `500`.

Why this matters: route-layer regressions are caught before pipeline internals are involved.

## 2) Pipeline Determinism Rails

Test module: `tests/services/test_summary_pipeline.py`

Protected behaviors:

- deterministic normalization and whitelist behavior for driver hash data,
- stable cache-key generation across row ordering and scalar type variants,
- payload validation for driver behaviour constraints,
- cache-hit short-circuit behavior,
- cache-miss orchestration behavior,
- zero-event branch skipping AI calls.

Example guarantee (from tests):

- equivalent payloads with differing row order and `"1"` vs `1` scalars produce identical cache keys.

## 3) Risk Determinism Rails

Test module: `tests/services/test_driver_risk_engine.py`

Protected behaviors:

- deterministic risk score calculations,
- stable risk-band classification thresholds,
- concern ranking semantics,
- model version and response-shape expectations for the risk facade.

Why this matters: deterministic risk must remain reproducible regardless of AI output.

## 4) AI Guardrail Rails

Test module: `tests/services/test_ai_summary.py`

Protected behaviors:

- prompt sanitization for driver and fleet summaries,
- prompt guardrail instruction presence,
- deterministic fallback behavior for empty/invalid payloads,
- deterministic fallback behavior on OpenAI client failures.

Why this matters: AI outputs remain bounded by safe deterministic input preparation.

## 5) Cache Integrity Rails

Test module: `tests/cache/test_cache_worker.py`

Protected behaviors:

- key validation rules,
- cache read/write correctness,
- expiry behavior for TTL-based fleet cache entries.

Why this matters: cache correctness is part of performance, consistency, and cost control.

## 6) Reading Tests as Architecture Documentation

When onboarding, read tests in this order:

1. `tests/api/test_api.py`
2. `tests/services/test_summary_pipeline.py`
3. `tests/services/test_driver_risk_engine.py`
4. `tests/services/test_ai_summary.py`
5. `tests/cache/test_cache_worker.py`

This progression mirrors runtime layering and shows how design constraints are enforced in executable form.