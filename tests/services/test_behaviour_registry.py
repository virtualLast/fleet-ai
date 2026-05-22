from services.risk.behaviour_registry import (
    BEHAVIOUR_DEFINITIONS,
    get_behaviour_definitions,
    get_behaviour_keys,
    get_behaviour_source_fields,
)


def test_behaviour_registry_includes_required_v2_source_fields():
    """What: Verify registry covers all required v2 behaviour source fields.

    Why: Missing behaviour mappings would silently exclude risk signals in feature extraction.
    How: Compare required field set against registry-derived source fields.
    """
    required_fields = {
        "adasFcwCount",
        "adasHmwCount",
        "adasPcwCount",
        "dsmFatigueCount",
        "dsmNoDriverCount",
        "dsmHandheldDevicesCount",
        "dsmSmokingCount",
        "dsmDistractionCount",
        "dsmYawningCount",
        "dsmSeatbeltCount",
    }

    source_fields = set(get_behaviour_source_fields().values())

    assert required_fields.issubset(source_fields)


def test_behaviour_registry_entries_contain_required_metadata_shape():
    """What: Verify each registry entry has required metadata keys.

    Why: Downstream extraction/classification modules depend on stable registry schema.
    How: Assert required keys and basic value constraints for all definitions.
    """
    required_keys = {"source_field", "severity_weight", "category", "label"}

    for key, definition in get_behaviour_definitions().items():
        assert required_keys.issubset(definition.keys())
        assert isinstance(definition["source_field"], str) and definition["source_field"]
        assert float(definition["severity_weight"]) > 0
        assert isinstance(definition["category"], str) and definition["category"]
        assert isinstance(definition["label"], str) and definition["label"]
        assert isinstance(key, str) and key


def test_behaviour_registry_keeps_independent_adas_behaviour_keys():
    """What: Verify ADAS signals remain separate behaviours in registry.

    Why: Breadth semantics require per-behaviour weighted diversity without category collapsing.
    How: Assert FCW/HMW/PCW are distinct registry keys and map to distinct source fields.
    """
    keys = set(get_behaviour_keys())
    fields = get_behaviour_source_fields()

    assert {"adas_fcw", "adas_hmw", "adas_pcw"}.issubset(keys)
    assert fields["adas_fcw"] != fields["adas_hmw"]
    assert fields["adas_hmw"] != fields["adas_pcw"]
    assert fields["adas_fcw"] != fields["adas_pcw"]


def test_behaviour_registry_iteration_order_is_stable():
    """What: Verify behaviour iteration order is deterministic.

    Why: Deterministic outputs require stable ordering in extraction and explainability lists.
    How: Compare helper-derived key order to literal registry insertion order.
    """
    assert get_behaviour_keys() == tuple(BEHAVIOUR_DEFINITIONS.keys())
