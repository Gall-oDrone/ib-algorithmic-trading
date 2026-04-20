"""Unit tests for corporate Postgres repository S3 archival behavior."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from corporate_data.exceptions import CorporateDataStorageError
from corporate_data.models import WshEventRecord
from corporate_data.storage.postgres_repository import PostgresCorporateDataRepository


def _sample_event() -> WshEventRecord:
    return WshEventRecord(
        req_id=900123,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        filter_payload={"conId": 265598},
        raw_json='{"conId":265598,"events":[{"event_type":"wshe_dividend"}]}',
        json_payload={"conId": 265598, "events": [{"event_type": "wshe_dividend"}]},
        yaml_payload="conId: 265598\nevents:\n- event_type: wshe_dividend\n",
        received_at_utc=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_insert_event_archives_json_yaml_to_s3(monkeypatch):
    s3_manager = MagicMock()
    repo = PostgresCorporateDataRepository(
        database_url="postgresql://localhost:5432/test",
        s3_manager=s3_manager,
        s3_bucket_name="my-bucket",
        s3_prefix="corporate_data/wsh_events",
        enable_s3_archive=True,
    )
    monkeypatch.setattr(repo, "_insert_event_in_postgres", lambda _event: None)

    repo.insert_event(_sample_event())

    assert s3_manager.upload_bytes.call_count == 3
    uploaded_keys = [call[1]["object_key"] for call in s3_manager.upload_bytes.call_args_list]
    assert any(key.endswith(".raw.json") for key in uploaded_keys)
    assert any(key.endswith(".parsed.json") for key in uploaded_keys)
    assert any(key.endswith(".yaml") for key in uploaded_keys)


def test_insert_event_raises_when_s3_enabled_without_bucket(monkeypatch):
    repo = PostgresCorporateDataRepository(
        database_url="postgresql://localhost:5432/test",
        s3_manager=None,
        s3_bucket_name=None,
        enable_s3_archive=True,
    )
    monkeypatch.setattr(repo, "_insert_event_in_postgres", lambda _event: None)

    with pytest.raises(CorporateDataStorageError, match="no S3 manager/bucket configured"):
        repo.insert_event(_sample_event())


def test_get_archived_event_by_req_id_downloads_json_yaml():
    s3_manager = MagicMock()
    s3_manager.list_objects.return_value = [
        "corporate_data/wsh_events/AAPL/req_900123_20260101T120000Z.raw.json",
        "corporate_data/wsh_events/AAPL/req_900123_20260101T120000Z.parsed.json",
        "corporate_data/wsh_events/AAPL/req_900123_20260101T120000Z.yaml",
    ]
    s3_manager.download_bytes.side_effect = [
        b'{"conId":265598,"events":[{"event_type":"wshe_dividend"}]}',
        b'{\n  "conId": 265598,\n  "events": [{"event_type":"wshe_dividend"}]\n}',
        b"conId: 265598\nevents:\n- event_type: wshe_dividend\n",
    ]
    repo = PostgresCorporateDataRepository(
        database_url="postgresql://localhost:5432/test",
        s3_manager=s3_manager,
        s3_bucket_name="my-bucket",
        enable_s3_archive=True,
    )

    payloads = repo.get_archived_event_by_req_id(req_id=900123, symbol="AAPL")

    assert "wshe_dividend" in payloads["raw_json"]
    assert "wshe_dividend" in payloads["json"]
    assert "wshe_dividend" in payloads["yaml"]


def test_get_archived_event_by_req_id_raises_when_not_found():
    s3_manager = MagicMock()
    s3_manager.list_objects.return_value = []
    repo = PostgresCorporateDataRepository(
        database_url="postgresql://localhost:5432/test",
        s3_manager=s3_manager,
        s3_bucket_name="my-bucket",
        enable_s3_archive=True,
    )

    with pytest.raises(CorporateDataStorageError, match="No S3 archived corporate event found"):
        repo.get_archived_event_by_req_id(req_id=900123)
