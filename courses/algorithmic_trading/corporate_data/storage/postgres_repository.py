"""PostgreSQL implementation of ICorporateDataRepository with optional S3 archival."""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

from aws.s3 import S3Manager
from corporate_data.exceptions import CorporateDataStorageError
from corporate_data.interfaces import ICorporateDataRepository
from corporate_data.models import WshEventRecord


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


class PostgresCorporateDataRepository(ICorporateDataRepository):
    """PostgreSQL repository for corporate WSH event payloads."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        s3_manager: Optional[S3Manager] = None,
        s3_bucket_name: Optional[str] = None,
        s3_prefix: Optional[str] = None,
        enable_s3_archive: Optional[bool] = None,
    ):
        self._database_url = (
            database_url
            or os.getenv("CORPORATE_DATA_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
            or "postgresql://localhost:5432/ib_streaming"
        )
        self._s3_bucket_name = (
            s3_bucket_name
            or os.getenv("CORPORATE_DATA_S3_BUCKET")
            or os.getenv("AWS_DEFAULT_BUCKET")
        )
        self._s3_prefix = (
            s3_prefix
            or os.getenv("CORPORATE_DATA_S3_PREFIX")
            or "corporate_data/wsh_events"
        ).strip("/")
        env_s3_enabled = os.getenv("CORPORATE_DATA_ENABLE_S3_ARCHIVE", "false").lower() == "true"
        self._enable_s3_archive = (
            enable_s3_archive if enable_s3_archive is not None else env_s3_enabled
        )
        self._s3_manager = s3_manager
        if self._enable_s3_archive and self._s3_manager is None and self._s3_bucket_name:
            self._s3_manager = S3Manager(
                bucket_name=self._s3_bucket_name,
                default_prefix=self._s3_prefix,
            )

    def insert_event(self, event: WshEventRecord) -> None:
        self._insert_event_in_postgres(event)
        if self._enable_s3_archive:
            self._archive_event_to_s3(event)

    def _insert_event_in_postgres(self, event: WshEventRecord) -> None:
        from psycopg2.extras import Json

        template = """
            INSERT INTO corporate_wsh_events (
                req_id, symbol, sec_type, exchange, filter_payload,
                raw_json, json_payload, yaml_payload, received_at_utc
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        row = (
            event.req_id,
            event.symbol,
            event.sec_type,
            event.exchange,
            Json(event.filter_payload),
            event.raw_json,
            Json(event.json_payload),
            event.yaml_payload,
            _to_ts(event.received_at_utc),
        )
        try:
            with _connection(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(template, row)
        except Exception as e:
            raise CorporateDataStorageError(f"insert_event failed: {e}") from e

    def _archive_event_to_s3(self, event: WshEventRecord) -> None:
        if not self._s3_manager or not self._s3_bucket_name:
            raise CorporateDataStorageError(
                "S3 archival enabled but no S3 manager/bucket configured."
            )

        timestamp = event.received_at_utc.strftime("%Y%m%dT%H%M%SZ")
        base_key = f"{event.symbol}/req_{event.req_id}_{timestamp}"
        metadata = {
            "symbol": event.symbol,
            "req_id": str(event.req_id),
            "sec_type": event.sec_type,
        }
        try:
            self._s3_manager.upload_bytes(
                object_key=f"{base_key}.raw.json",
                data=event.raw_json.encode("utf-8"),
                metadata=metadata,
            )
            self._s3_manager.upload_bytes(
                object_key=f"{base_key}.parsed.json",
                data=json.dumps(event.json_payload, indent=2).encode("utf-8"),
                metadata=metadata,
            )
            self._s3_manager.upload_bytes(
                object_key=f"{base_key}.yaml",
                data=event.yaml_payload.encode("utf-8"),
                metadata=metadata,
            )
        except Exception as e:
            raise CorporateDataStorageError(f"S3 archival failed: {e}") from e

    def get_archived_event_by_req_id(
        self,
        req_id: int,
        symbol: Optional[str] = None,
    ) -> Dict[str, str]:
        """Fetch archived WSH payloads from S3 by request ID."""
        if not self._s3_manager or not self._s3_bucket_name:
            raise CorporateDataStorageError(
                "S3 retrieval requested but no S3 manager/bucket configured."
            )

        prefix = f"{symbol}/" if symbol else ""
        try:
            object_keys = self._s3_manager.list_objects(prefix=prefix)
            base_matches = [
                key.rsplit(".", 2)[0]
                for key in object_keys
                if f"req_{req_id}_" in key and key.endswith(".raw.json")
            ]
            if not base_matches:
                raise CorporateDataStorageError(
                    f"No S3 archived corporate event found for req_id={req_id}."
                )

            base_key = sorted(base_matches)[-1]
            return {
                "raw_json": self._s3_manager.download_bytes(f"{base_key}.raw.json").decode("utf-8"),
                "json": self._s3_manager.download_bytes(f"{base_key}.parsed.json").decode("utf-8"),
                "yaml": self._s3_manager.download_bytes(f"{base_key}.yaml").decode("utf-8"),
            }
        except CorporateDataStorageError:
            raise
        except Exception as e:
            raise CorporateDataStorageError(
                f"S3 retrieval failed for req_id={req_id}: {e}"
            ) from e
