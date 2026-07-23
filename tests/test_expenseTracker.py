"""Unit tests for the console front end (expenseTracker.py).

These cover the console's own responsibilities — input prompting, validation
loops, and printed output. Data/aggregation correctness is covered separately
in test_expense_store.py. A temporary ExpenseStore keeps the real data file
untouched.

Run from the project root with:
    python -m unittest discover -s tests -t . -v
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Headless matplotlib before importing the module (produceGraph builds a figure).
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402
matplotlib.use("Agg")

import expenseTracker  # noqa: E402
from expense_store import Expense, ExpenseStore  # noqa: E402


class StoreBackedTestCase(unittest.TestCase):
    """Provides a throwaway ExpenseStore pointed at a temp file."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.remove(self.path)
        self.store = ExpenseStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        matplotlib.pyplot.close("all")


class PositiveAmountCheckTests(unittest.TestCase):
    def test_accepts_first_positive_value(self):
        with patch("builtins.input", side_effect=["10"]):
            self.assertEqual(expenseTracker.positiveAmountCheck(), 10.0)

    def test_reprompts_until_positive(self):
        with patch("builtins.input", side_effect=["-5", "0", "12.5"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(expenseTracker.positiveAmountCheck(), 12.5)

    def test_reprompts_on_non_numeric_input(self):
        # Non-numeric and empty input must not crash; the prompt re-asks.
        with patch("builtins.input", side_effect=["abc", "", "7"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(expenseTracker.positiveAmountCheck(), 7.0)


class SelectExpenseTypeTests(unittest.TestCase):
    def test_returns_type_at_selected_index(self):
        with patch("builtins.input", side_effect=["3"]), redirect_stdout(io.StringIO()):
            self.assertEqual(
                expenseTracker.selectExpenseType(), expenseTracker.EXPENSE_TYPES[2]
            )

    def test_rejects_invalid_then_accepts_valid(self):
        with patch("builtins.input", side_effect=["0", "99", "abc", "1"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(
                expenseTracker.selectExpenseType(), expenseTracker.EXPENSE_TYPES[0]
            )


class ReadDateTests(unittest.TestCase):
    def test_accepts_valid_iso(self):
        with patch("builtins.input", side_effect=["2025-06-15"]):
            self.assertEqual(expenseTracker.readDate(), ("2025", "06", "15"))

    def test_today(self):
        now = datetime.now()
        with patch("builtins.input", side_effect=["today"]):
            self.assertEqual(
                expenseTracker.readDate(),
                (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")),
            )

    def test_reprompts_on_invalid(self):
        with patch("builtins.input", side_effect=["nope", "2024-01-02"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(expenseTracker.readDate(), ("2024", "01", "02"))


class AddExpenseTests(StoreBackedTestCase):
    def test_writes_expense_via_store(self):
        inputs = ["12.5", "3", "weekly shop", "2025-06-15"]  # amount, type#, details, date
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense(self.store)

        loaded = self.store.load()
        self.assertEqual(len(loaded), 1)
        e = loaded[0]
        self.assertEqual(
            (e.iso_date, e.category, e.amount, e.details),
            ("2025-06-15", expenseTracker.EXPENSE_TYPES[2], 12.5, "weekly shop"),
        )

    def test_blank_details_stored_as_empty(self):
        inputs = ["40", "1", "", "2024-01-02"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense(self.store)
        self.assertEqual(self.store.load()[0].details, "")


class ViewSummaryTests(StoreBackedTestCase):
    def _run(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            expenseTracker.viewSummary(self.store)
        return buf.getvalue()

    def test_empty_reports_no_expenses(self):
        self.assertIn("No expenses recorded yet", self._run())

    def test_total_and_grouping_and_details(self):
        for e in [
            Expense("2025", "07", "05", "Food", 10.0),
            Expense("2023", "06", "18", "Shopping", 42.99),
            Expense("2026", "07", "23", "Dining out", 70.0, "dinner"),
            Expense("2026", "07", "24", "Housing", 20.0),
        ]:
            self.store.add(e)
        out = self._run()

        self.assertIn("Your total expense is  142.99", out)
        self.assertLess(out.index("2023-06"), out.index("2025-07"))
        self.assertLess(out.index("2025-07"), out.index("2026-07"))

        # Per-month subtotal must be the month's own sum (70 + 20), not the grand total.
        self.assertIn("2026-07 (subtotal: 90.00)", out)

        lines = out.splitlines()
        dining = next(line for line in lines if "Dining out" in line)
        housing = next(line for line in lines if "Housing" in line)
        self.assertIn("— dinner", dining)
        self.assertNotIn("—", housing)


class ProduceGraphTests(StoreBackedTestCase):
    def setUp(self):
        super().setUp()
        # Importing the GUI module elsewhere flips the global backend to TkAgg;
        # force headless Agg here so building a figure never needs a live window.
        matplotlib.pyplot.switch_backend("Agg")

    def test_calls_show_with_data(self):
        self.store.add(Expense("2025", "06", "15", "Food", 12.5))
        with patch.object(expenseTracker.plt, "show") as show, redirect_stdout(io.StringIO()):
            expenseTracker.produceGraph(self.store)
        show.assert_called_once()

    def test_empty_reports_and_skips_show(self):
        with patch.object(expenseTracker.plt, "show") as show:
            buf = io.StringIO()
            with redirect_stdout(buf):
                expenseTracker.produceGraph(self.store)
        self.assertIn("No expenses to graph yet", buf.getvalue())
        show.assert_not_called()


class MainDispatchTests(unittest.TestCase):
    def _run_choice(self, choice):
        """Run main() with a single menu choice then exit; return the 3 handler mocks."""
        with patch.object(expenseTracker, "addExpense") as add, \
                patch.object(expenseTracker, "viewSummary") as view, \
                patch.object(expenseTracker, "produceGraph") as graph, \
                patch("builtins.input", side_effect=[choice, "4"]), \
                redirect_stdout(io.StringIO()):
            expenseTracker.main()
        return add, view, graph

    def test_choice_1_calls_add_only(self):
        add, view, graph = self._run_choice("1")
        add.assert_called_once()
        view.assert_not_called()
        graph.assert_not_called()

    def test_choice_2_calls_view_only(self):
        add, view, graph = self._run_choice("2")
        view.assert_called_once()
        add.assert_not_called()
        graph.assert_not_called()

    def test_choice_3_calls_graph_only(self):
        add, view, graph = self._run_choice("3")
        graph.assert_called_once()
        add.assert_not_called()
        view.assert_not_called()

    def test_invalid_choice_is_reported(self):
        with patch("builtins.input", side_effect=["x", "4"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                expenseTracker.main()
        self.assertIn("Invalid input", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
