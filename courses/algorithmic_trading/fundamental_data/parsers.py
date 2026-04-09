"""Parser helpers for IB fundamental XML payloads."""

import json
import xml.etree.ElementTree as ET
from typing import Any, Dict

import yaml

from fundamental_data.exceptions import FundamentalDataParseError


def parse_to_xml(xml_payload: str) -> ET.Element:
    """Parse raw payload to XML element tree root."""
    try:
        return ET.fromstring(xml_payload)
    except ET.ParseError as e:
        raise FundamentalDataParseError(f"Invalid XML payload: {e}") from e


def _element_to_dict(node: ET.Element) -> Dict[str, Any]:
    children = list(node)
    payload: Dict[str, Any] = {}

    if node.attrib:
        payload["@attributes"] = dict(node.attrib)

    text = (node.text or "").strip()
    if text:
        payload["#text"] = text

    if not children:
        return payload

    for child in children:
        child_dict = _element_to_dict(child)
        if child.tag in payload:
            if not isinstance(payload[child.tag], list):
                payload[child.tag] = [payload[child.tag]]
            payload[child.tag].append(child_dict)
        else:
            payload[child.tag] = child_dict
    return payload


def parse_to_json(xml_payload: str) -> Dict[str, Any]:
    """Parse XML payload into a JSON-serializable dictionary."""
    root = parse_to_xml(xml_payload)
    return {root.tag: _element_to_dict(root)}


def parse_to_yaml(xml_payload: str) -> str:
    """Parse XML payload and return YAML representation."""
    json_payload = parse_to_json(xml_payload)
    return yaml.safe_dump(json_payload, sort_keys=False)


def parse_to_xml_string(xml_payload: str) -> str:
    """Validate XML and return normalized XML string."""
    root = parse_to_xml(xml_payload)
    return ET.tostring(root, encoding="unicode")


def parse_to_json_string(xml_payload: str) -> str:
    """Parse XML payload and return pretty JSON string."""
    return json.dumps(parse_to_json(xml_payload), indent=2)
