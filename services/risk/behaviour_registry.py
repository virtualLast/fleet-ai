"""Central behaviour registry for deterministic risk-engine v2 modules."""

from __future__ import annotations


BEHAVIOUR_DEFINITIONS = {
    "adas_fcw": {
        "source_field": "adasFcwCount",
        "severity_weight": 5.0,
        "category": "adas",
        "label": "Forward Collision Warning",
    },
    "adas_hmw": {
        "source_field": "adasHmwCount",
        "severity_weight": 4.0,
        "category": "adas",
        "label": "Headway Monitoring Warning",
    },
    "adas_pcw": {
        "source_field": "adasPcwCount",
        "severity_weight": 4.0,
        "category": "adas",
        "label": "Pedestrian Collision Warning",
    },
    "dsm_fatigue": {
        "source_field": "dsmFatigueCount",
        "severity_weight": 5.0,
        "category": "attention",
        "label": "Fatigue",
    },
    "dsm_no_driver": {
        "source_field": "dsmNoDriverCount",
        "severity_weight": 4.0,
        "category": "compliance",
        "label": "No Driver Detected",
    },
    "dsm_handheld_devices": {
        "source_field": "dsmHandheldDevicesCount",
        "severity_weight": 4.0,
        "category": "attention",
        "label": "Handheld Device Use",
    },
    "dsm_smoking": {
        "source_field": "dsmSmokingCount",
        "severity_weight": 2.0,
        "category": "compliance",
        "label": "Smoking",
    },
    "dsm_distraction": {
        "source_field": "dsmDistractionCount",
        "severity_weight": 4.0,
        "category": "attention",
        "label": "Distraction",
    },
    "dsm_yawning": {
        "source_field": "dsmYawningCount",
        "severity_weight": 3.0,
        "category": "attention",
        "label": "Yawning",
    },
    "dsm_seatbelt": {
        "source_field": "dsmSeatbeltCount",
        "severity_weight": 3.0,
        "category": "compliance",
        "label": "Seatbelt",
    },
}


def get_behaviour_definitions() -> dict:
    """Return immutable-order behaviour definitions for deterministic iteration."""

    return BEHAVIOUR_DEFINITIONS


def get_behaviour_keys() -> tuple[str, ...]:
    """Return ordered behaviour keys used by risk extraction and dimensions."""

    return tuple(BEHAVIOUR_DEFINITIONS.keys())


def get_behaviour_source_fields() -> dict[str, str]:
    """Return mapping of behaviour key to normalized source field name."""

    return {
        behaviour_key: definition["source_field"]
        for behaviour_key, definition in BEHAVIOUR_DEFINITIONS.items()
    }