from types import SimpleNamespace

import pytest

from app.costs import BudgetExceeded, check_budget


class FakeConn:
    def __init__(self, spent):
        self.spent = spent

    def execute(self, *args, **kwargs):
        spent = self.spent
        return SimpleNamespace(fetchone=lambda: {"spent": spent})


SETTINGS = SimpleNamespace(max_budget_usd=1.0)


def test_under_budget_passes():
    check_budget(FakeConn(0.2), SETTINGS)


def test_at_or_over_budget_raises():
    with pytest.raises(BudgetExceeded):
        check_budget(FakeConn(1.0), SETTINGS)
    with pytest.raises(BudgetExceeded):
        check_budget(FakeConn(5.0), SETTINGS)
