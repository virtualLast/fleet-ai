"""Typed deterministic models for Behavioural Risk Engine v2."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BehaviourMetrics:
    """Represent extracted deterministic metrics for a single behaviour."""

    raw_event_count: int = 0
    journey_presence_count: int = 0
    journey_ratio: float = 0.0
    max_single_journey_events: int = 0
    weighted_score: float = 0.0


@dataclass(frozen=True)
class RiskFeatures:
    """Represent extracted feature payload before risk dimension evaluation."""

    journey_count: int = 0
    active_behaviour_count: int = 0
    high_severity_journey_count: int = 0
    behaviour_metrics: dict[str, BehaviourMetrics] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskAssessment:
    """Represent final deterministic assessment payload and explainability metadata."""

    model_version: str
    overall_risk_level: str
    overall_risk_score: float
    assessment_confidence: str
    primary_concerns: list[str]
    requires_intervention: bool
    dimensions: dict[str, dict] = field(default_factory=dict)
    explainability: dict[str, object] = field(default_factory=dict)
    intervention: dict[str, object] = field(default_factory=dict)
