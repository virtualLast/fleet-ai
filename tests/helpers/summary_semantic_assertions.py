import re


BEHAVIOUR_SYNONYMS = {
    "fatigue": ["fatigue", "drowsy", "drowsiness", "tiredness", "exhaustion"],
    "distraction": ["distraction", "distracted", "attention lapse"],
    "handheld_device": ["handheld", "phone", "mobile device", "device use"],
    "seatbelt": ["seatbelt", "seat belt", "restraint"],
    "smoking": ["smoking", "smoke", "cigarette", "tobacco"],
    "aggression": ["aggressive", "aggression", "road rage"],
}

TONE_KEYWORDS = {
    "disciplinary": ["disciplinary", "discipline", "penalty", "sanction"],
    "critical": ["critical", "severe", "dangerous", "highly concerning"],
    "urgent": ["urgent", "immediate", "right away", "urgent intervention"],
    "supportive": ["supportive", "reassuring", "encouraging", "positive", "routine monitoring", "maintain this standard"],
    "coaching": ["coaching", "coach", "guidance", "improvement plan"],
    "cautious": ["cautious", "limited", "narrow", "preliminary", "low confidence"],
}


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_any(text: str, phrases: list[str]) -> bool:
    normalized_text = _normalized(text)
    return any(_normalized(phrase) in normalized_text for phrase in phrases if phrase)


def assert_required_phrases(summary: str, required: list[str]) -> None:
    for phrase in required or []:
        if not _contains_any(summary, [phrase]):
            raise AssertionError(f"Missing required phrase/concept: {phrase}")


def assert_preferred_phrases(summary: str, preferred: list[str]) -> list[str]:
    missing = []
    for phrase in preferred or []:
        if not _contains_any(summary, [phrase]):
            missing.append(phrase)
    return missing


def assert_forbidden_phrases(summary: str, forbidden: list[str]) -> None:
    for phrase in forbidden or []:
        if _contains_any(summary, [phrase]):
            raise AssertionError(f"Forbidden phrase/concept present: {phrase}")


def assert_required_concepts(summary: str, required_concepts: list[str]) -> None:
    concept_checks = {
        "low_confidence_cautious": ["limited", "narrow", "cautious", "preliminary", "low confidence"],
        "single_pattern_acknowledged": ["single pattern", "single-pattern", "narrow pattern", "limited pattern"],
        "high_confidence_firm": ["clear", "consistent", "strong signal", "high confidence"],
        "multi_risk_acknowledged": ["multiple", "fatigue", "distraction"],
        "positive_reassurance": ["safe", "reassuring", "positive", "no tracked", "maintain this standard"],
        "no_concerns": ["no primary concerns", "no major concerns", "no significant concerns", "no tracked", "routine monitoring"],
    }

    for concept in required_concepts or []:
        phrases = concept_checks.get(concept)
        if not phrases:
            continue
        if not _contains_any(summary, phrases):
            raise AssertionError(f"Missing required semantic concept: {concept}")


def assert_summary_consistent_with_risk_profile(summary: str, risk_profile: dict) -> None:
    confidence = (risk_profile or {}).get("confidence")
    risk_level = (risk_profile or {}).get("risk_level")
    primary_concerns = (risk_profile or {}).get("primary_concerns") or []

    if confidence == "low":
        if not _contains_any(summary, ["low confidence", "limited", "cautious", "preliminary", "narrow"]):
            raise AssertionError("Low-confidence profile requires cautious/uncertain wording")

    if risk_level == "low":
        assert_forbidden_phrases(summary, ["dangerous", "severe", "critical", "urgent intervention", "highly concerning"])

    if not primary_concerns:
        assert_forbidden_phrases(summary, ["major concern", "critical concern", "key concern"])


def assert_behaviour_consistency(summary: str, behaviour_summary: dict, forbidden_when_absent: list[str]) -> None:
    behaviour_to_count = {
        "fatigue": int((behaviour_summary or {}).get("fatigue_events", 0) or 0),
        "distraction": int((behaviour_summary or {}).get("distraction_events", 0) or 0),
        "handheld_device": int((behaviour_summary or {}).get("handheld_device_events", 0) or 0),
        "seatbelt": int((behaviour_summary or {}).get("seatbelt_events", 0) or 0),
        "smoking": int((behaviour_summary or {}).get("smoking_events", 0) or 0),
        "aggression": 0,
    }

    for behaviour in forbidden_when_absent or []:
        if behaviour_to_count.get(behaviour, 0) > 0:
            continue
        synonyms = BEHAVIOUR_SYNONYMS.get(behaviour, [behaviour])
        if _contains_any(summary, synonyms):
            raise AssertionError(f"Summary references absent behaviour '{behaviour}'")


def assert_tones(summary: str, required_tones: list[str], forbidden_tones: list[str]) -> None:
    for tone in required_tones or []:
        if tone not in TONE_KEYWORDS:
            continue
        if not _contains_any(summary, TONE_KEYWORDS[tone]):
            raise AssertionError(f"Missing required tone: {tone}")

    for tone in forbidden_tones or []:
        if tone not in TONE_KEYWORDS:
            continue
        if _contains_any(summary, TONE_KEYWORDS[tone]):
            raise AssertionError(f"Forbidden tone present: {tone}")