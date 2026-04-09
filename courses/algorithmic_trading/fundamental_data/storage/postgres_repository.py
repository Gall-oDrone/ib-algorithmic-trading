"""PostgreSQL implementation of IFundamentalDataRepository."""

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fundamental_data.exceptions import FundamentalDataStorageError
from fundamental_data.interfaces import IFundamentalDataRepository
from fundamental_data.models import FundamentalReportRecord


def _to_ts(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@contextmanager
def _connection(database_url: str):
    import psycopg2

    conn = psycopg2.connect(database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class PostgresFundamentalDataRepository(IFundamentalDataRepository):
    """PostgreSQL repository for fundamental XML/JSON/YAML reports."""

    def __init__(self, database_url: Optional[str] = None):
        self._database_url = (
            database_url
            or os.getenv("FUNDAMENTAL_DATA_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
            or "postgresql://localhost:5432/ib_streaming"
        )

    def insert_report(self, report: FundamentalReportRecord) -> None:
        from psycopg2.extras import Json

        template = """
            INSERT INTO fundamental_data_reports (
                req_id, symbol, sec_type, exchange, report_type,
                xml_payload, json_payload, yaml_payload, received_at_utc
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        row = (
            report.req_id,
            report.symbol,
            report.sec_type,
            report.exchange,
            report.report_type,
            report.xml_payload,
            Json(report.json_payload),
            report.yaml_payload,
            _to_ts(report.received_at_utc),
        )
        try:
            with _connection(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(template, row)
        except Exception as e:
            raise FundamentalDataStorageError(f"insert_report failed: {e}") from e
