"""Shared normalization helpers for summary dataset payloads."""


def safe_int(value, fallback=0):
    """Convert value to int with fallback when coercion fails."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def safe_text(value, default=""):
    """Convert value to stripped text with default for null inputs."""

    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def normalize_summary_dataset(
    raw_data: list[dict],
    *,
    int_fields: tuple[str, ...] = (),
    text_fields: tuple[str, ...] = (),
    int_defaults: dict[str, int] | None = None,
    text_defaults: dict[str, str] | None = None,
    sort_keys: tuple[str, ...] = (),
) -> list[dict]:
    """Normalize rows using shared int/text coercion and optional stable sorting."""

    normalized_rows = []
    int_defaults = int_defaults or {}
    text_defaults = text_defaults or {}

    if sort_keys:
        allowed_fields = set(int_fields) | set(text_fields)
        invalid_sort_keys = [key for key in sort_keys if key not in allowed_fields]

        if invalid_sort_keys:
            raise ValueError(
                "Invalid sort_keys fields: "
                f"{invalid_sort_keys}. sort_keys must be present in int_fields/text_fields."
            )

    for row in raw_data:
        if not isinstance(row, dict):
            continue

        normalized_row = {}

        for field in int_fields:
            default_value = int_defaults.get(field, 0)
            normalized_row[field] = safe_int(row.get(field, default_value), default_value)

        for field in text_fields:
            default_value = text_defaults.get(field, "")
            normalized_row[field] = safe_text(row.get(field), default_value)

        normalized_rows.append(normalized_row)

    if sort_keys:
        normalized_rows.sort(key=lambda row: tuple(row[key] for key in sort_keys))

    return normalized_rows