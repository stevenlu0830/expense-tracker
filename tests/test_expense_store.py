"""Unit tests for the shared domain/persistence layer (expense_store.py).

Run from the project root with:
    python -m unittest discover -s tests -t . -v
"""

import csv
import os
import sys
import tempfile
import unittest
from datetime import datetime

# Make the project root importable when tests live in this subfolder.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from expense_store import (  # noqa: E402
    EXPENSE_TYPES,
    Expense,
    ExpenseStore,
    MonthGroup,
    group_by_month,
    monthly_totals,
    parse_date,
    total,
)


class ExpenseTypesTests(unittest.TestCase):
    def test_expected_membership_and_size(self):
        self.assertEqual(len(EXPENSE_TYPES), 22)
        self.assertIn("Housing", EXPENSE_TYPES)
        self.assertIn("Others", EXPENSE_TYPES)


class ParseDateTests(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(parse_date("2025-06-15"), ("2025", "06", "15"))

    def test_today_keyword_uses_current_date(self):
        now = datetime.now()
        self.assertEqual(
            parse_date("today"),
            (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")),
        )

    def test_blank_uses_current_date(self):
        now = datetime.now()
        self.assertEqual(parse_date("   "), (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")))

    def test_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_date("15/06/2025")


class ExpenseModelTests(unittest.TestCase):
    def test_month_key_and_iso_date(self):
        e = Expense("2025", "06", "15", "Food", 12.5, "lunch")
        self.assertEqual(e.month_key, "2025-06")
        self.assertEqual(e.iso_date, "2025-06-15")

    def test_from_row_six_columns(self):
        e = Expense.from_row(["2025", "06", "15", "Food", "12.50", "lunch"])
        self.assertEqual(e.amount, 12.5)
        self.assertEqual(e.details, "lunch")

    def test_from_row_five_columns_defaults_details(self):
        e = Expense.from_row(["2025", "06", "15", "Food", "12.50"])
        self.assertEqual(e.details, "")

    def test_from_row_too_few_columns_raises(self):
        with self.assertRaises(ValueError):
            Expense.from_row(["2025", "06", "15", "Food"])

    def test_from_row_bad_amount_raises(self):
        with self.assertRaises(ValueError):
            Expense.from_row(["2025", "06", "15", "Food", "abc"])

    def test_to_row_roundtrip(self):
        e = Expense("2025", "06", "15", "Food", 12.5, "lunch")
        self.assertEqual(e.to_row(), ["2025", "06", "15", "Food", 12.5, "lunch"])


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.remove(self.path)  # start with a non-existent file
        self.store = ExpenseStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _write_rows(self, rows):
        with open(self.path, "w", newline="") as f:
            csv.writer(f).writerows(rows)

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(self.store.load(), [])

    def test_add_then_load_roundtrip(self):
        self.store.add(Expense("2025", "06", "15", "Food", 12.5, "lunch"))
        loaded = self.store.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].category, "Food")
        self.assertEqual(loaded[0].amount, 12.5)
        self.assertEqual(loaded[0].details, "lunch")

    def test_add_appends(self):
        self.store.add(Expense("2025", "01", "01", "Housing", 100.0))
        self.store.add(Expense("2025", "02", "02", "Groceries", 5.0))
        self.assertEqual(len(self.store.load()), 2)

    def test_load_skips_blank_rows(self):
        # A trailing newline or stray blank line yields an empty row from the
        # csv reader; it should be skipped without disturbing the real rows.
        self._write_rows([
            ["2025", "06", "15", "Food", "12.50", "ok"],
            [],
            ["2025", "06", "17", "Food", "8.00"],
        ])
        self.assertEqual([e.amount for e in self.store.load()], [12.5, 8.0])

    def test_load_skips_malformed_rows(self):
        self._write_rows([
            ["2025", "06", "15", "Food", "12.50", "ok"],
            ["garbage"],                       # too few columns
            ["2025", "06", "16", "Food", "NaN-ish"],  # bad amount
            ["2025", "06", "17", "Food", "8.00"],
        ])
        loaded = self.store.load()
        self.assertEqual(len(loaded), 2)
        self.assertEqual([e.amount for e in loaded], [12.5, 8.0])


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.expenses = [
            Expense("2025", "07", "05", "Food", 10.0),
            Expense("2023", "06", "18", "Shopping", 42.99),
            Expense("2025", "06", "30", "Food", 2.0),
            Expense("2025", "06", "15", "Food", 3.0, "lunch"),
            Expense("2025", "06", "17", "Food", 8.0),
        ]

    def test_total(self):
        self.assertAlmostEqual(total(self.expenses), 65.99)

    def test_total_empty(self):
        self.assertEqual(total([]), 0)

    def test_group_by_month_orders_groups_oldest_to_latest(self):
        keys = [g.month_key for g in group_by_month(self.expenses)]
        self.assertEqual(keys, ["2023-06", "2025-06", "2025-07"])

    def test_group_by_month_orders_entries_by_day(self):
        june = next(g for g in group_by_month(self.expenses) if g.month_key == "2025-06")
        self.assertEqual([e.day for e in june.expenses], ["15", "17", "30"])

    def test_group_by_month_subtotal(self):
        june = next(g for g in group_by_month(self.expenses) if g.month_key == "2025-06")
        self.assertAlmostEqual(june.subtotal, 13.0)

    def test_group_by_month_preserves_details(self):
        june = next(g for g in group_by_month(self.expenses) if g.month_key == "2025-06")
        first = june.expenses[0]
        self.assertEqual((first.day, first.details), ("15", "lunch"))

    def test_monthly_totals_ordered_and_summed(self):
        self.assertEqual(
            monthly_totals(self.expenses),
            [("2023-06", 42.99), ("2025-06", 13.0), ("2025-07", 10.0)],
        )

    def test_monthly_totals_empty(self):
        self.assertEqual(monthly_totals([]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
