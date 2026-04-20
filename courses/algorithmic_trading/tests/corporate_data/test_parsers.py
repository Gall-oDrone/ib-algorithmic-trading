"""Unit tests for corporate WSH parser helpers."""

import json

import pytest
import yaml

from corporate_data.exceptions import CorporateDataParseError
from corporate_data.parsers import parse_wsh_json, parse_wsh_json_string, parse_wsh_yaml


SAMPLE_WSH_JSON = """
{
  "conId": 265598,
  "events": [
    {"event_type": "wshe_dividend", "payment_date": "2026-02-15"},
    {"event_type": "wshe_split", "split_from": 1, "split_to": 2}
  ]
}
""".strip()


def test_parse_wsh_json_returns_dict():
    payload = parse_wsh_json(SAMPLE_WSH_JSON)
    assert payload["conId"] == 265598
    assert payload["events"][0]["event_type"] == "wshe_dividend"


def test_parse_wsh_json_string_returns_valid_json():
    payload_str = parse_wsh_json_string(SAMPLE_WSH_JSON)
    payload = json.loads(payload_str)
    assert payload["events"][1]["event_type"] == "wshe_split"


def test_parse_wsh_yaml_returns_yaml_text():
    payload_yaml = parse_wsh_yaml(SAMPLE_WSH_JSON)
    payload = yaml.safe_load(payload_yaml)
    assert payload["events"][0]["payment_date"] == "2026-02-15"


def test_parse_wsh_json_raises_on_invalid_json():
    with pytest.raises(CorporateDataParseError, match="Invalid WSH JSON payload"):
        parse_wsh_json("{invalid-json")


def test_parse_wsh_json_raises_on_non_object():
    with pytest.raises(CorporateDataParseError, match="must decode to a JSON object"):
        parse_wsh_json('["not", "an", "object"]')
