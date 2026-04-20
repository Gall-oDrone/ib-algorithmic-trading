-- Corporate WSH event payloads captured via reqWshEventData.

CREATE TABLE IF NOT EXISTS corporate_wsh_events (
    id BIGSERIAL PRIMARY KEY,
    req_id INTEGER NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    sec_type VARCHAR(16) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    filter_payload JSONB NOT NULL,
    raw_json TEXT NOT NULL,
    json_payload JSONB NOT NULL,
    yaml_payload TEXT NOT NULL,
    received_at_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_corporate_wsh_symbol_received
    ON corporate_wsh_events (symbol, received_at_utc);
