## Corporate WSH Data

This module integrates IBKR Wall Street Horizon (WSH) event data into the project with:

- request flow: `reqWshEventData`
- callback flow: `wshEventData`
- persistence: Postgres + optional S3 archival
- helper CLI: `scripts/request_corporate_wsh_events.py`

### Quick Start

```bash
python3 courses/algorithmic_trading/scripts/request_corporate_wsh_events.py \
  --con-id 265598 \
  --symbol AAPL \
  --filter "wshe_ed|wshe_div|wshe_split" \
  --start-date 20260101 \
  --end-date 20261231 \
  --total-limit 10
```

Multi-symbol in-flight example:

```bash
python3 courses/algorithmic_trading/scripts/request_corporate_wsh_events.py \
  --symbols "NVDA,TSLA,GOOG,AAPL" \
  --con-ids "4815747,76792991,208813720,265598" \
  --con-id 265598 \
  --max-concurrency 2 \
  --request-delay-ms 250 \
  --filter "wshe_ed|wshe_div|wshe_split"
```

### Recommended Filter Presets

Use `--filter` to scope event categories:

- Earnings only: `wshe_ed`
- Dividends only: `wshe_div`
- Splits only: `wshe_split`
- Earnings + dividends: `wshe_ed|wshe_div`
- Corporate actions bundle: `wshe_div|wshe_split|wshe_spinoff|wshe_merger`
- Broad events bundle: `wshe_ed|wshe_div|wshe_split|wshe_board|wshe_guidance`

Note: actual supported tags depend on IBKR/WSH backend and entitlement level.

### Exit Codes (CLI)

- `0`: Success. Event received and persisted.
- `2`: Could not connect to TWS/IB Gateway.
- `3`: Missing WSH entitlement (IB error `10276`).
- `4`: No event received within timeout.
- `5`: Invalid multi-symbol argument shape (`--symbols` and `--con-ids` count mismatch).
- `6`: Invalid pacing configuration (`--max-concurrency` must be > 0).

### Output Files

By default, the CLI writes payload snapshots into:

- `courses/algorithmic_trading/data/corporate_wsh_events`

For each request, it stores:

- `req_<req_id>_<symbol>.raw.json`
- `req_<req_id>_<symbol>.json`
- `req_<req_id>_<symbol>.yaml`

Disable file output with `--skip-file-output`.

### Operational Notes

- Ensure TWS/IB Gateway is running and API-enabled.
- Provide a valid `--con-id` for instrument-specific requests.
- Keep `--total-limit` conservative in production loops.
- Tune `--max-concurrency` and `--request-delay-ms` to pace IB requests in large batches.
- If entitlement is missing, the CLI exits with code `3` and no failure tracebacks.
