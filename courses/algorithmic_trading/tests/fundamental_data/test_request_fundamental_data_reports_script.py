"""Tests for request_fundamental_data_reports CLI helper functions."""

import argparse
from pathlib import Path

import pytest

from scripts.request_fundamental_data_reports import (
    build_output_base,
    chunk_requests,
    resolve_symbols,
    save_payload_files,
)


def test_build_output_base(tmp_path: Path):
    output = build_output_base(
        output_dir=tmp_path, req_id=800123, symbol="AAPL", report_type="ReportSnapshot"
    )
    assert output.name == "req_800123_AAPL_ReportSnapshot"


def test_save_payload_files_writes_xml_json_yaml(tmp_path: Path):
    output_base = tmp_path / "req_800123_AAPL_ReportSnapshot"
    payloads = {
        "xml": "<ReportSnapshot />",
        "json": '{"ReportSnapshot": {}}',
        "yaml": "ReportSnapshot: {}\n",
    }
    written = save_payload_files(output_base, payloads)

    assert written["xml"].exists()
    assert written["json"].exists()
    assert written["yaml"].exists()
    assert written["xml"].read_text(encoding="utf-8") == "<ReportSnapshot />"


def test_resolve_symbols_single():
    args = argparse.Namespace(symbol="AAPL", symbols="")
    assert resolve_symbols(args) == ["AAPL"]


def test_resolve_symbols_multiple():
    args = argparse.Namespace(symbol="AAPL", symbols="NVDA,TSLA,GOOG,AAPL")
    assert resolve_symbols(args) == ["NVDA", "TSLA", "GOOG", "AAPL"]


def test_chunk_requests_splits_by_max_concurrency():
    batch = [{"req_id": i} for i in range(5)]
    chunks = chunk_requests(batch, max_concurrency=3)
    assert [len(chunk) for chunk in chunks] == [3, 2]


def test_chunk_requests_raises_on_invalid_concurrency():
    with pytest.raises(ValueError, match="greater than zero"):
        chunk_requests([{"req_id": 1}], max_concurrency=-1)
