"""Storage subpackage: interface and PostgreSQL implementation."""

from fundamental_data.storage.repository import IFundamentalDataRepository
from fundamental_data.storage.postgres_repository import PostgresFundamentalDataRepository

__all__ = ["IFundamentalDataRepository", "PostgresFundamentalDataRepository"]
