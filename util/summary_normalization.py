"""Shared normalization helpers for summary dataset payloads."""

from typing import Any

NormalizedValue = int | str
NormalizedRow = dict[str, NormalizedValue]


def safe_int(value: Any, fallback: int = 0) -> int:
    """Convert value to int with fallback when coercion fails."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def safe_text(value: Any, default: str = "") -> str:
    """Convert value to stripped text with default for null inputs."""

    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def normalize_summary_dataset(
    raw_data: list[dict[str, Any]],
    *,
    int_fields: tuple[str, ...] = (),
    text_fields: tuple[str, ...] = (),
    int_defaults: dict[str, int] | None = None,
    text_defaults: dict[str, str] | None = None,
    sort_keys: tuple[str, ...] = (),
) -> list[NormalizedRow]:
    """Normalize summary rows with deterministic field coercion and optional stable sorting.

    Args:
        raw_data: Source rows to normalize; non-dict rows are ignored.
        int_fields: Integer field names to include in each normalized row.
        text_fields: Text field names to include in each normalized row.
        int_defaults: Optional per-field defaults for integer coercion.
        text_defaults: Optional per-field defaults for text coercion.
        sort_keys: Optional deterministic sort keys; must be subset of selected fields.

    Returns:
        A new list of normalized dictionaries containing only selected int/text fields.

    Side effects:
        None.

    Raises:
        ValueError: If any key in `sort_keys` is missing from `int_fields` and `text_fields`.
    """

    normalized_rows: list[NormalizedRow] = []
    resolved_int_defaults = int_defaults or {}
    resolved_text_defaults = text_defaults or {}

    if sort_keys:
        allowed_fields = set(int_fields) | set(text_fields)
        invalid_sort_keys = [key for key in sort_keys if key not in allowed_fields]

        if invalid_sort_keys:
            raise ValueError(
                f"Invalid sort_keys fields: {invalid_sort_keys}. sort_keys must be present in int_fields/text_fields."
            )

    for row in raw_data:
        if not isinstance(row, dict):
            continue

        normalized_row: NormalizedRow = {}

        for field in int_fields:
            int_default_value = resolved_int_defaults.get(field, 0)
            normalized_row[field] = safe_int(row.get(field, int_default_value), int_default_value)

        for field in text_fields:
            text_default_value = resolved_text_defaults.get(field, "")
            normalized_row[field] = safe_text(row.get(field), text_default_value)

        normalized_rows.append(normalized_row)

    if sort_keys:
        normalized_rows.sort(key=lambda row: tuple(row[key] for key in sort_keys))

    return normalized_rows
