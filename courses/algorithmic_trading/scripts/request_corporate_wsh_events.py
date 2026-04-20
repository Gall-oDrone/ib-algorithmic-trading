#!/usr/bin/env python3
"""Request IBKR WSH corporate events and optionally save payloads to files."""

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
from corporate_data.storage.postgres_repository import PostgresCorporateDataRepository
from corporate_data.wsh.client import (
    CorporateDataCallbackHandler,
    IBCorporateDataClient,
    next_corporate_req_id,
)


def build_output_base(output_dir: Path, req_id: int, symbol: str) -> Path:
    """Build deterministic output base path for payload files."""
    return output_dir / f"req_{req_id}_{symbol}"


def save_payload_files(output_base: Path, payloads: Dict[str, str]) -> Dict[str, Path]:
    """Write raw json, parsed json and yaml payloads to disk."""
    output_base.parent.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    for ext, key in (("raw.json", "raw_json"), ("json", "json"), ("yaml", "yaml")):
        path = output_base.with_suffix(f".{ext}")
        path.write_text(payloads[key], encoding="utf-8")
        written[key] = path
    return written


class _InMemoryEventRepo:
    """Captures first event from callback while still persisting to Postgres repository."""

    def __init__(self, persisted_repo: PostgresCorporateDataRepository):
        self.persisted_repo = persisted_repo
        self.events_by_req_id: Dict[int, object] = {}

    def insert_event(self, event) -> None:
        self.persisted_repo.insert_event(event)
        self.events_by_req_id[event.req_id] = event


class WshCliApp(EWrapper, EClient):
    """App routing WSH callbacks to the corporate data handler."""

    def __init__(self, handler: CorporateDataCallbackHandler):
        EClient.__init__(self, self)
        self._handler = handler
        self.connected = False
        self.entitlement_error: Optional[str] = None
        self.last_error: Optional[Tuple[int, int, str]] = None

    def nextValidId(self, orderId):
        self.connected = True

    def wshEventData(self, reqId, dataJson):
        self._handler.wsh_event_data(reqId, dataJson)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        self.last_error = (reqId, errorCode, errorString)
        self._handler.on_ib_error(reqId, errorCode, errorString)
        if errorCode == 10276:
            self.entitlement_error = errorString


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Request and store corporate WSH events from IBKR.")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Ticker symbol (default: AAPL).")
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated symbols for concurrent requests (e.g. NVDA,TSLA,GOOG,AAPL).",
    )
    parser.add_argument("--con-id", type=int, required=True, help="IB contract ID (conId).")
    parser.add_argument(
        "--con-ids",
        type=str,
        default="",
        help="Comma-separated conIds matching --symbols order.",
    )
    parser.add_argument("--sec-type", type=str, default="STK", help="Security type (default: STK).")
    parser.add_argument("--exchange", type=str, default="SMART", help="Exchange (default: SMART).")
    parser.add_argument("--currency", type=str, default="USD", help="Currency (default: USD).")
    parser.add_argument(
        "--filter",
        type=str,
        default="wshe_ed|wshe_div|wshe_split",
        help="WSH filter expression.",
    )
    parser.add_argument("--start-date", type=str, default="", help="YYYYMMDD start date.")
    parser.add_argument("--end-date", type=str, default="", help="YYYYMMDD end date.")
    parser.add_argument("--total-limit", type=int, default=10, help="Max number of events.")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="Max wait time.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "corporate_wsh_events"),
        help="Directory to write first received payload as files.",
    )
    parser.add_argument(
        "--skip-file-output",
        action="store_true",
        help="If set, do not write payload files to disk.",
    )
    return parser.parse_args()


def _csv_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_symbol_conid_pairs(args: argparse.Namespace) -> List[Tuple[str, int]]:
    """Resolve single or multi-symbol inputs into request pairs."""
    symbols = _csv_list(args.symbols)
    con_ids = _csv_list(args.con_ids)
    if not symbols:
        return [(args.symbol, args.con_id)]
    if len(symbols) != len(con_ids):
        raise ValueError("When --symbols is used, --con-ids must have the same count.")
    return list(zip(symbols, [int(item) for item in con_ids]))


def main() -> int:
    args = parse_args()
    config = get_config()

    postgres_repo = PostgresCorporateDataRepository()
    memory_repo = _InMemoryEventRepo(postgres_repo)
    handler = CorporateDataCallbackHandler(memory_repo)
    app = WshCliApp(handler)

    app.connect(config.host, config.port, clientId=3121)
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    time.sleep(2)

    if not app.isConnected():
        print("Could not connect to TWS/IB Gateway. Verify API is enabled and session is running.")
        return 2

    client = IBCorporateDataClient(app, handler)
    try:
        symbol_conid_pairs = build_symbol_conid_pairs(args)
    except ValueError as e:
        print(str(e))
        return 5

    request_batch = []
    req_ids = []
    for symbol, con_id in symbol_conid_pairs:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = args.sec_type
        contract.exchange = args.exchange
        contract.currency = args.currency
        contract.conId = con_id

        req_id = next_corporate_req_id()
        req_ids.append(req_id)
        filter_payload = {
            "conId": con_id,
            "filter": args.filter,
            "fillWatchlist": False,
            "fillPortfolio": False,
            "startDate": args.start_date,
            "endDate": args.end_date,
            "totalLimit": args.total_limit,
        }
        request_batch.append(
            {"req_id": req_id, "contract": contract, "filter_payload": filter_payload}
        )
    client.request_wsh_event_data_batch(request_batch)

    deadline = time.time() + args.timeout_seconds
    while (
        time.time() < deadline
        and app.entitlement_error is None
        and len(memory_repo.events_by_req_id) < len(req_ids)
    ):
        time.sleep(0.25)

    app.disconnect()

    if app.entitlement_error:
        print(f"WSH entitlement missing: {app.entitlement_error}")
        return 3

    if not memory_repo.events_by_req_id:
        print("No WSH event payload received before timeout for any request.")
        if app.last_error:
            req, code, message = app.last_error
            print(f"Last IB error: reqId={req}, code={code}, message={message}")
        return 4

    print(
        f"Received {len(memory_repo.events_by_req_id)}/{len(req_ids)} "
        "WSH payload(s) before timeout."
    )
    for req_id in req_ids:
        event = memory_repo.events_by_req_id.get(req_id)
        if not event:
            print(f"- Missing payload for req_id={req_id}")
            continue
        print(
            f"- Stored event req_id={event.req_id} symbol={event.symbol} "
            f"keys={list(event.json_payload.keys())}"
        )

    if args.skip_file_output:
        return 0

    for req_id in req_ids:
        event = memory_repo.events_by_req_id.get(req_id)
        if not event:
            continue
        payloads = {
            "raw_json": event.raw_json,
            "json": json.dumps(event.json_payload, indent=2),
            "yaml": event.yaml_payload,
        }
        output_base = build_output_base(Path(args.output_dir).resolve(), event.req_id, event.symbol)
        written = save_payload_files(output_base, payloads)
        print(f"- RAW JSON: {written['raw_json']}")
        print(f"- JSON:     {written['json']}")
        print(f"- YAML:     {written['yaml']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
