"""Unit tests for fundamental XML parser helpers."""

import json

import pytest
import yaml

from fundamental_data.exceptions import FundamentalDataParseError
from fundamental_data.parsers import (
    parse_to_json,
    parse_to_json_string,
    parse_to_xml,
    parse_to_xml_string,
    parse_to_yaml,
)


SAMPLE_XML = """
<ReportSnapshot>
  <Company>
    <Name>Apple Inc</Name>
    <ISIN>US0378331005</ISIN>
  </Company>
  <Ratios>
    <PE>30.1</PE>
  </Ratios>
</ReportSnapshot>
""".strip()


def test_parse_to_xml_returns_root_element():
    root = parse_to_xml(SAMPLE_XML)
    assert root.tag == "ReportSnapshot"


def test_parse_to_xml_string_normalizes_xml():
    xml_string = parse_to_xml_string(SAMPLE_XML)
    assert "<ReportSnapshot>" in xml_string
    assert "<Name>Apple Inc</Name>" in xml_string


def test_parse_to_json_maps_nested_elements():
    payload = parse_to_json(SAMPLE_XML)
    assert payload["ReportSnapshot"]["Company"]["Name"]["#text"] == "Apple Inc"
    assert payload["ReportSnapshot"]["Ratios"]["PE"]["#text"] == "30.1"


def test_parse_to_json_string_is_valid_json():
    payload_str = parse_to_json_string(SAMPLE_XML)
    payload = json.loads(payload_str)
    assert payload["ReportSnapshot"]["Company"]["ISIN"]["#text"] == "US0378331005"


def test_parse_to_yaml_returns_yaml_text():
    payload_yaml = parse_to_yaml(SAMPLE_XML)
    payload = yaml.safe_load(payload_yaml)
    assert payload["ReportSnapshot"]["Company"]["Name"]["#text"] == "Apple Inc"


def test_parse_to_xml_raises_on_invalid_xml():
    with pytest.raises(FundamentalDataParseError, match="Invalid XML payload"):
        parse_to_xml("<ReportSnapshot><Broken></ReportSnapshot>")
