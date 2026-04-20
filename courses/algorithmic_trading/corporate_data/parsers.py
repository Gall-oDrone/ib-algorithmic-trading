"""Parser helpers for IBKR WSH JSON payloads."""

import json
from typing import Any, Dict

import yaml

from corporate_data.exceptions import CorporateDataParseError


def parse_wsh_json(payload: str) -> Dict[str, Any]:
    """Parse raw WSH payload into JSON dict."""
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as e:
        raise CorporateDataParseError(f"Invalid WSH JSON payload: {e}") from e

    if not isinstance(parsed, dict):
        raise CorporateDataParseError("WSH payload must decode to a JSON object")
    return parsed


def parse_wsh_yaml(payload: str) -> str:
    """Parse WSH payload and return YAML representation."""
    return yaml.safe_dump(parse_wsh_json(payload), sort_keys=False)


def parse_wsh_json_string(payload: str) -> str:
    """Normalize WSH payload and return pretty JSON string."""
    return json.dumps(parse_wsh_json(payload), indent=2)
