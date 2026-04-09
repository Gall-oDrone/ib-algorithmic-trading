"""Pytest fixtures for fundamental data tests."""

import sys
from pathlib import Path
from typing import List

import pytest

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fundamental_data.interfaces import IFundamentalDataRepository
from fundamental_data.models import FundamentalReportRecord


class InMemoryFundamentalDataRepository(IFundamentalDataRepository):
    """In-memory repository for unit tests."""

    def __init__(self):
        self.reports: List[FundamentalReportRecord] = []

    def insert_report(self, report: FundamentalReportRecord) -> None:
        self.reports.append(report)


@pytest.fixture
def in_memory_fundamental_repo():
    return InMemoryFundamentalDataRepository()
