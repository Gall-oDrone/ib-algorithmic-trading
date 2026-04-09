"""Fundamental data module: IB reqFundamentalData + XML/JSON/YAML transforms."""

from fundamental_data.exceptions import (
    FundamentalDataConfigurationError,
    FundamentalDataError,
    FundamentalDataParseError,
    FundamentalDataRequestIdExhaustedError,
    FundamentalDataStorageError,
)
from fundamental_data.interfaces import IFundamentalDataClient, IFundamentalDataRepository
from fundamental_data.models import FundamentalReportRecord
from fundamental_data.parsers import (
    parse_to_json,
    parse_to_json_string,
    parse_to_xml,
    parse_to_xml_string,
    parse_to_yaml,
)

__all__ = [
    "FundamentalDataError",
    "FundamentalDataStorageError",
    "FundamentalDataConfigurationError",
    "FundamentalDataParseError",
    "FundamentalDataRequestIdExhaustedError",
    "IFundamentalDataClient",
    "IFundamentalDataRepository",
    "FundamentalReportRecord",
    "parse_to_xml",
    "parse_to_xml_string",
    "parse_to_json",
    "parse_to_json_string",
    "parse_to_yaml",
]
