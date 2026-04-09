"""Unit tests for fundamental data models."""

from datetime import datetime

import pytest

from fundamental_data.models import FundamentalReportRecord


def test_fundamental_report_record_creation():
    record = FundamentalReportRecord(
        req_id=800001,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        report_type="ReportSnapshot",
        xml_payload="<ReportSnapshot><Company><Name>Apple</Name></Company></ReportSnapshot>",
        json_payload={"ReportSnapshot": {"Company": {"Name": {"#text": "Apple"}}}},
        yaml_payload="ReportSnapshot:\n  Company:\n    Name:\n      '#text': Apple\n",
        received_at_utc=datetime.utcnow(),
    )
    assert record.symbol == "AAPL"
    assert record.report_type == "ReportSnapshot"
    assert record.received_at_utc.tzinfo is not None


def test_fundamental_report_record_requires_non_empty_xml():
    with pytest.raises(ValueError, match="xml_payload must be a non-empty XML string"):
        FundamentalReportRecord(
            req_id=1,
            symbol="AAPL",
            sec_type="STK",
            exchange="SMART",
            report_type="ReportSnapshot",
            xml_payload="  ",
            json_payload={},
            yaml_payload="{}",
            received_at_utc=datetime.utcnow(),
        )
