"""Unit tests for corporate data models."""

from datetime import datetime

import pytest

from corporate_data.models import WshEventRecord


def test_wsh_event_record_creation():
    record = WshEventRecord(
        req_id=900001,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        filter_payload={"conId": 265598},
        raw_json='{"conId":265598,"events":[{"event_type":"wshe_dividend"}]}',
        json_payload={"conId": 265598, "events": [{"event_type": "wshe_dividend"}]},
        yaml_payload="conId: 265598\nevents:\n- event_type: wshe_dividend\n",
        received_at_utc=datetime.utcnow(),
    )
    assert record.symbol == "AAPL"
    assert record.filter_payload["conId"] == 265598
    assert record.received_at_utc.tzinfo is not None


def test_wsh_event_record_requires_non_empty_json():
    with pytest.raises(ValueError, match="raw_json must be a non-empty JSON string"):
        WshEventRecord(
            req_id=1,
            symbol="AAPL",
            sec_type="STK",
            exchange="SMART",
            filter_payload={},
            raw_json=" ",
            json_payload={},
            yaml_payload="{}",
            received_at_utc=datetime.utcnow(),
        )
