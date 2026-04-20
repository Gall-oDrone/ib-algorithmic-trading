"""Tests for request_fundamental_data_reports CLI helper functions."""

import argparse
from pathlib import Path

from scripts.request_fundamental_data_reports import (
    build_output_base,
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
