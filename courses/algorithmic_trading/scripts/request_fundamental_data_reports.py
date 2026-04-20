#!/usr/bin/env python3
"""Request IBKR fundamental reports and optionally save payloads to files."""

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_config
from fundamental_data.fundamentals.client import (
    FundamentalDataCallbackHandler,
    IBFundamentalDataClient,
    next_fundamental_req_id,
)
from fundamental_data.storage.postgres_repository import PostgresFundamentalDataRepository


def build_output_base(output_dir: Path, req_id: int, symbol: str, report_type: str) -> Path:
    """Build deterministic output base path for payload files."""
    return output_dir / f"req_{req_id}_{symbol}_{report_type}"


def save_payload_files(output_base: Path, payloads: Dict[str, str]) -> Dict[str, Path]:
    """Write xml, json and yaml payloads to disk."""
    output_base.parent.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    for ext in ("xml", "json", "yaml"):
        path = output_base.with_suffix(f".{ext}")
        path.write_text(payloads[ext], encoding="utf-8")
        written[ext] = path
    return written


def _csv_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_symbols(args: argparse.Namespace) -> List[str]:
    """Resolve single or multi-symbol inputs into a symbol list."""
    symbols = _csv_list(args.symbols)
    if symbols:
        return symbols
    return [args.symbol]


class _InMemoryFundamentalRepo:
    """Captures reports from callback while still persisting in Postgres."""

    def __init__(self, persisted_repo: PostgresFundamentalDataRepository):
        self.persisted_repo = persisted_repo
        self.reports_by_req_id: Dict[int, object] = {}

    def insert_report(self, report) -> None:
        self.persisted_repo.insert_report(report)
        self.reports_by_req_id[report.req_id] = report


class FundamentalCliApp(EWrapper, EClient):
    """App routing fundamental callbacks to the fundamental data handler."""

    def __init__(self, handler: FundamentalDataCallbackHandler):
        EClient.__init__(self, self)
        self._handler = handler
        self.connected = False
        self.last_error: Optional[Tuple[int, int, str]] = None

    def nextValidId(self, orderId):
        self.connected = True

    def fundamentalData(self, reqId, data):
        self._handler.fundamental_data(reqId, data)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        self.last_error = (reqId, errorCode, errorString)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Request and store fundamental reports from IBKR.")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Ticker symbol (default: AAPL).")
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated symbols for concurrent requests (e.g. NVDA,TSLA,GOOG,AAPL).",
    )
    parser.add_argument("--sec-type", type=str, default="STK", help="Security type (default: STK).")
    parser.add_argument("--exchange", type=str, default="SMART", help="Exchange (default: SMART).")
    parser.add_argument("--currency", type=str, default="USD", help="Currency (default: USD).")
    parser.add_argument(
        "--report-type",
        type=str,
        default="ReportSnapshot",
        help="Fundamental report type.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=20, help="Max wait time.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "fundamental_reports"),
        help="Directory to write received payload files.",
    )
    parser.add_argument(
        "--skip-file-output",
        action="store_true",
        help="If set, do not write payload files to disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = get_config()
    symbols = resolve_symbols(args)

    postgres_repo = PostgresFundamentalDataRepository()
    memory_repo = _InMemoryFundamentalRepo(postgres_repo)
    handler = FundamentalDataCallbackHandler(memory_repo)
    app = FundamentalCliApp(handler)

    app.connect(config.host, config.port, clientId=3122)
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    time.sleep(2)

    if not app.isConnected():
        print("Could not connect to TWS/IB Gateway. Verify API is enabled and session is running.")
        return 2

    client = IBFundamentalDataClient(app, handler)
    request_batch = []
    req_ids = []
    for symbol in symbols:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = args.sec_type
        contract.exchange = args.exchange
        contract.currency = args.currency
        req_id = next_fundamental_req_id()
        req_ids.append(req_id)
        request_batch.append(
            {"req_id": req_id, "contract": contract, "report_type": args.report_type}
        )

    client.request_fundamental_data_batch(request_batch)

    deadline = time.time() + args.timeout_seconds
    while time.time() < deadline and len(memory_repo.reports_by_req_id) < len(req_ids):
        time.sleep(0.25)

    app.disconnect()

    if not memory_repo.reports_by_req_id:
        print("No fundamental report payload received before timeout for any request.")
        if app.last_error:
            req, code, message = app.last_error
            print(f"Last IB error: reqId={req}, code={code}, message={message}")
        return 4

    print(
        f"Received {len(memory_repo.reports_by_req_id)}/{len(req_ids)} "
        "fundamental payload(s) before timeout."
    )
    for req_id in req_ids:
        report = memory_repo.reports_by_req_id.get(req_id)
        if not report:
            print(f"- Missing payload for req_id={req_id}")
            continue
        keys = list(report.json_payload.keys())
        print(f"- Stored report req_id={report.req_id} symbol={report.symbol} keys={keys}")

    if args.skip_file_output:
        return 0

    for req_id in req_ids:
        report = memory_repo.reports_by_req_id.get(req_id)
        if not report:
            continue
        payloads = {
            "xml": report.xml_payload,
            "json": json.dumps(report.json_payload, indent=2),
            "yaml": report.yaml_payload,
        }
        output_base = build_output_base(
            Path(args.output_dir).resolve(),
            report.req_id,
            report.symbol,
            report.report_type,
        )
        written = save_payload_files(output_base, payloads)
        print(f"- XML:  {written['xml']}")
        print(f"- JSON: {written['json']}")
        print(f"- YAML: {written['yaml']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
