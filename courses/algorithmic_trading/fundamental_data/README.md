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
  --report-type ReportSnapshot
```

### Exit Codes (CLI)

- `0`: Success. At least one payload received.
- `2`: Could not connect to TWS/IB Gateway.
- `4`: No payload received within timeout.

### Output Files

By default, the CLI writes payload snapshots into:

- `courses/algorithmic_trading/data/fundamental_reports`

For each request, it stores:

- `req_<req_id>_<symbol>_<report_type>.xml`
- `req_<req_id>_<symbol>_<report_type>.json`
- `req_<req_id>_<symbol>_<report_type>.yaml`

Disable file output with `--skip-file-output`.
