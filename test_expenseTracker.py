"""Unit tests for the console app (expenseTracker.py).

Run from the project root with:  python -m unittest test_expenseTracker -v

These tests never touch the real expenses.csv: each test runs inside a fresh
temporary working directory, and the module reads/writes the file relative to
the current directory.
"""

import csv
import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import patch, MagicMock

# Force a non-interactive matplotlib backend before importing the module, so
# produceGraph() never tries to open a real window during tests.
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib
matplotlib.use("Agg")

import expenseTracker


def read_csv(path="expenses.csv"):
    with open(path, newline="") as f:
        return [row for row in csv.reader(f) if row]


class TempCwdTestCase(unittest.TestCase):
    """Base case: isolate each test in its own temporary working directory."""

    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="ettest_")
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)
        matplotlib.pyplot.close("all")

    def write_csv(self, rows, path="expenses.csv"):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)


class PositiveAmountCheckTests(TempCwdTestCase):
    def test_accepts_first_positive_value(self):
        with patch("builtins.input", side_effect=["10"]):
            self.assertEqual(expenseTracker.positiveAmountCheck(), 10.0)

    def test_reprompts_until_positive(self):
        # -5 and 0 are rejected; 12.5 is accepted.
        with patch("builtins.input", side_effect=["-5", "0", "12.5"]):
            self.assertEqual(expenseTracker.positiveAmountCheck(), 12.5)


class SelectExpenseTypeTests(TempCwdTestCase):
    def test_returns_type_at_selected_index(self):
        # Choice "3" -> third item in EXPENSE_TYPES.
        with patch("builtins.input", side_effect=["3"]), redirect_stdout(io.StringIO()):
            self.assertEqual(
                expenseTracker.selectExpenseType(), expenseTracker.EXPENSE_TYPES[2]
            )

    def test_rejects_invalid_then_accepts_valid(self):
        # 0 (too low), 99 (too high), "abc" (non-digit) rejected; then "1".
        with patch("builtins.input", side_effect=["0", "99", "abc", "1"]), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(
                expenseTracker.selectExpenseType(), expenseTracker.EXPENSE_TYPES[0]
            )


class AddExpenseTests(TempCwdTestCase):
    def test_writes_row_with_explicit_date_and_details(self):
        inputs = ["12.5", "3", "weekly shop", "2025-06-15"]  # amount, type#, details, date
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense()

        rows = read_csv()
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0],
            ["2025", "06", "15", expenseTracker.EXPENSE_TYPES[2], "12.5", "weekly shop"],
        )

    def test_blank_details_stored_as_empty(self):
        inputs = ["40", "1", "", "2024-01-02"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense()

        rows = read_csv()
        self.assertEqual(rows[0][5], "")

    def test_appends_without_overwriting(self):
        self.write_csv([["2025", "01", "01", "Housing", "100.0", "old"]])
        inputs = ["5", "2", "note", "2025-02-02"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense()

        rows = read_csv()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][5], "old")

    def test_today_uses_current_date(self):
        inputs = ["7", "1", "", "today"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(io.StringIO()):
            expenseTracker.addExpense()

        rows = read_csv()
        today = datetime.now()
        self.assertEqual(rows[0][0], today.strftime("%Y"))
        self.assertEqual(rows[0][1], today.strftime("%m"))
        self.assertEqual(rows[0][2], today.strftime("%d"))


class ViewSummaryTests(TempCwdTestCase):
    def _run_summary(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            expenseTracker.viewSummary()
        return buf.getvalue()

    def test_total_and_grouping_order_oldest_to_latest(self):
        self.write_csv([
            ["2025", "07", "05", "Food", "10.00", ""],
            ["2023", "06", "18", "Shopping", "42.99", ""],
            ["2025", "06", "16", "Entertainment", "25.00", ""],
        ])
        out = self._run_summary()

        self.assertIn("Your total expense is  77.99", out)
        # Month headers must appear oldest -> latest.
        self.assertLess(out.index("2023-06"), out.index("2025-06"))
        self.assertLess(out.index("2025-06"), out.index("2025-07"))

    def test_within_month_sorted_by_day(self):
        self.write_csv([
            ["2025", "06", "30", "Food", "2.00", ""],
            ["2025", "06", "15", "Food", "3.00", ""],
            ["2025", "06", "17", "Food", "8.00", ""],
        ])
        out = self._run_summary()
        self.assertLess(out.index("2025-06-15"), out.index("2025-06-17"))
        self.assertLess(out.index("2025-06-17"), out.index("2025-06-30"))

    def test_subtotal_per_month(self):
        self.write_csv([
            ["2025", "06", "15", "Food", "12.50", ""],
            ["2025", "06", "16", "Food", "7.50", ""],
        ])
        out = self._run_summary()
        self.assertIn("2025-06 (subtotal: 20.00)", out)

    def test_details_shown_when_present_and_omitted_when_blank(self):
        self.write_csv([
            ["2026", "07", "23", "Dining out", "70.00", "dinner"],
            ["2026", "07", "24", "Housing", "20.00", ""],
        ])
        out = self._run_summary()
        lines = out.splitlines()
        dining = next(line for line in lines if "Dining out" in line)
        housing = next(line for line in lines if "Housing" in line)
        self.assertIn("— dinner", dining)
        self.assertNotIn("—", housing)

    def test_legacy_five_column_rows_still_work(self):
        # Rows written before the details column existed have only 5 fields.
        self.write_csv([["2025", "05", "31", "Groceries", "5.50"]])
        out = self._run_summary()
        self.assertIn("Groceries: 5.50", out)
        self.assertNotIn("—", out)

    def test_missing_file_reports_error(self):
        # No expenses.csv created in this fresh temp dir.
        out = self._run_summary()
        self.assertIn("Cannot find expenses.csv", out)


class ProduceGraphTests(TempCwdTestCase):
    def setUp(self):
        super().setUp()
        # Importing the GUI module elsewhere flips the global backend to TkAgg;
        # force headless Agg here so building a figure never needs a live window.
        matplotlib.pyplot.switch_backend("Agg")

    def test_runs_and_calls_show_with_valid_data(self):
        self.write_csv([
            ["2025", "06", "15", "Food", "12.50", ""],
            ["2025", "07", "01", "Rent", "1200.00", "monthly"],
        ])
        with patch.object(expenseTracker.plt, "show") as mock_show, \
                redirect_stdout(io.StringIO()):
            expenseTracker.produceGraph()
        mock_show.assert_called_once()

    def test_missing_file_reports_error_and_skips_show(self):
        with patch.object(expenseTracker.plt, "show") as mock_show:
            buf = io.StringIO()
            with redirect_stdout(buf):
                expenseTracker.produceGraph()
        self.assertIn("Cannot find expenses.csv", buf.getvalue())
        mock_show.assert_not_called()


class MainDispatchTests(TempCwdTestCase):
    def test_menu_routes_choices_then_exits(self):
        with patch.object(expenseTracker, "addExpense") as add, \
                patch.object(expenseTracker, "viewSummary") as view, \
                patch.object(expenseTracker, "produceGraph") as graph, \
                patch("builtins.input", side_effect=["1", "2", "3", "4"]), \
                redirect_stdout(io.StringIO()):
            expenseTracker.main()
        add.assert_called_once()
        view.assert_called_once()
        graph.assert_called_once()

    def test_invalid_choice_is_reported(self):
        with patch("builtins.input", side_effect=["x", "4"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                expenseTracker.main()
        self.assertIn("Invalid input", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
