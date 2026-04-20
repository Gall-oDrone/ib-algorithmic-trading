"""Pytest fixtures for corporate data tests."""

import sys
from pathlib import Path
from typing import List

import pytest

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from corporate_data.interfaces import ICorporateDataRepository
from corporate_data.models import WshEventRecord


class InMemoryCorporateDataRepository(ICorporateDataRepository):
    """In-memory repository for unit tests."""

    def __init__(self):
        self.events: List[WshEventRecord] = []

    def insert_event(self, event: WshEventRecord) -> None:
        self.events.append(event)


@pytest.fixture
def in_memory_corporate_repo():
    return InMemoryCorporateDataRepository()
