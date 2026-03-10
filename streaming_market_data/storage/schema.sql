-- Streaming market data: ticks and snapshots
-- Run against your PostgreSQL database (e.g. STREAMING_MARKET_DATA_DB_URL or test DB).

CREATE TABLE IF NOT EXISTS market_data_ticks (
    id BIGSERIAL PRIMARY KEY,
    req_id INTEGER NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    sec_type VARCHAR(16) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    tick_type VARCHAR(16) NOT NULL,
    time_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    price DOUBLE PRECISION,
    size INTEGER,
    bid_price DOUBLE PRECISION,
    ask_price DOUBLE PRECISION,
    bid_size INTEGER,
    ask_size INTEGER,
    created_at_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_market_data_ticks_symbol_time ON market_data_ticks (symbol, time_utc);
CREATE INDEX IF NOT EXISTS idx_market_data_ticks_req_id ON market_data_ticks (req_id);

CREATE TABLE IF NOT EXISTS market_data_snapshots (
    id BIGSERIAL PRIMARY KEY,
    req_id INTEGER NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    sec_type VARCHAR(16) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    last DOUBLE PRECISION,
    bid_size INTEGER,
    ask_size INTEGER,
    last_size INTEGER,
    volume INTEGER,
    snapshot_time_utc TIMESTAMP WITH TIME ZONE,
    created_at_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_market_data_snapshots_symbol_time ON market_data_snapshots (symbol, snapshot_time_utc);
