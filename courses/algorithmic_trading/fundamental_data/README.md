## Fundamental Data

This module integrates IBKR `reqFundamentalData` reports with:

- request flow: `reqFundamentalData`
- callback flow: `fundamentalData`
- persistence: Postgres + optional S3 archival
- helper CLI: `scripts/request_fundamental_data_reports.py`

### Quick Start

```bash
python3 courses/algorithmic_trading/scripts/request_fundamental_data_reports.py \
  --symbol AAPL \
  --report-type ReportSnapshot
```

Multi-symbol in-flight example:

```bash
python3 courses/algorithmic_trading/scripts/request_fundamental_data_reports.py \
  --symbols "NVDA,TSLA,GOOG,AAPL" \
  --max-concurrency 2 \
  --request-delay-ms 250 \
  --report-type ReportSnapshot
```

### Exit Codes (CLI)

- `0`: Success. At least one payload received.
- `2`: Could not connect to TWS/IB Gateway.
- `4`: No payload received within timeout.
- `6`: Invalid pacing configuration (`--max-concurrency` must be > 0).

### Output Files

By default, the CLI writes payload snapshots into:

- `courses/algorithmic_trading/data/fundamental_reports`

For each request, it stores:

- `req_<req_id>_<symbol>_<report_type>.xml`
- `req_<req_id>_<symbol>_<report_type>.json`
- `req_<req_id>_<symbol>_<report_type>.yaml`

Disable file output with `--skip-file-output`.

For larger symbol batches, tune:

- `--max-concurrency` to cap in-flight requests per submission burst.
- `--request-delay-ms` to pause between bursts and avoid pacing issues.
