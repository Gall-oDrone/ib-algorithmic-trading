-- Fundamental data reports captured via reqFundamentalData.

CREATE TABLE IF NOT EXISTS fundamental_data_reports (
    id BIGSERIAL PRIMARY KEY,
    req_id INTEGER NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    sec_type VARCHAR(16) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    report_type VARCHAR(64) NOT NULL,
    xml_payload TEXT NOT NULL,
    json_payload JSONB NOT NULL,
    yaml_payload TEXT NOT NULL,
    received_at_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_fundamental_reports_symbol_received
    ON fundamental_data_reports (symbol, received_at_utc);
CREATE INDEX IF NOT EXISTS idx_fundamental_reports_report_type
    ON fundamental_data_reports (report_type);
