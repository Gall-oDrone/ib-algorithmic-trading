"""Tests for request_corporate_wsh_events CLI helper functions."""

from pathlib import Path

from scripts.request_corporate_wsh_events import build_output_base, save_payload_files


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
