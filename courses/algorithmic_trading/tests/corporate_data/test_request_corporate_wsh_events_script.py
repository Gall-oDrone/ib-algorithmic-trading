"""Tests for request_corporate_wsh_events CLI helper functions."""

import argparse
from pathlib import Path

import pytest

from scripts.request_corporate_wsh_events import (
    build_output_base,
    build_symbol_conid_pairs,
    chunk_requests,
    save_payload_files,
)


def test_build_output_base(tmp_path: Path):
    output = build_output_base(output_dir=tmp_path, req_id=900123, symbol="AAPL")
    assert output.name == "req_900123_AAPL"


def test_save_payload_files_writes_raw_json_json_yaml(tmp_path: Path):
    output_base = tmp_path / "req_900123_AAPL"
    payloads = {
        "raw_json": '{"k":"v"}',
        "json": '{\n  "k": "v"\n}',
        "yaml": "k: v\n",
    }
    written = save_payload_files(output_base, payloads)

    assert written["raw_json"].exists()
    assert written["json"].exists()
    assert written["yaml"].exists()
    assert written["raw_json"].read_text(encoding="utf-8") == '{"k":"v"}'


def test_build_symbol_conid_pairs_single_request():
    args = argparse.Namespace(symbol="AAPL", con_id=265598, symbols="", con_ids="")
    assert build_symbol_conid_pairs(args) == [("AAPL", 265598)]


def test_build_symbol_conid_pairs_multiple_requests():
    args = argparse.Namespace(
        symbol="AAPL",
        con_id=265598,
        symbols="NVDA,TSLA,GOOG,AAPL",
        con_ids="4815747,76792991,208813720,265598",
    )
    assert build_symbol_conid_pairs(args) == [
        ("NVDA", 4815747),
        ("TSLA", 76792991),
        ("GOOG", 208813720),
        ("AAPL", 265598),
    ]


def test_build_symbol_conid_pairs_raises_on_mismatch():
    args = argparse.Namespace(
        symbol="AAPL",
        con_id=265598,
        symbols="NVDA,TSLA",
        con_ids="4815747",
    )
    with pytest.raises(ValueError, match="must have the same count"):
        build_symbol_conid_pairs(args)


def test_chunk_requests_splits_by_max_concurrency():
    batch = [{"req_id": i} for i in range(5)]
    chunks = chunk_requests(batch, max_concurrency=2)
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_chunk_requests_raises_on_invalid_concurrency():
    with pytest.raises(ValueError, match="greater than zero"):
        chunk_requests([{"req_id": 1}], max_concurrency=0)
