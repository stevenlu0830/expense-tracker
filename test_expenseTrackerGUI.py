"""Unit tests for the GUI app (expenseTrackerGUI.py).

Run from the project root with:  python -m unittest test_expenseTrackerGUI -v

Tkinter needs its C extension (`_tkinter`) and a usable display. When either is
missing (e.g. a Homebrew Python built without Tk, or a headless CI box), every
test here is skipped rather than failing — so importing the GUI module is done
lazily, only after we confirm a Tk root can actually be created.
"""

import csv
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch


def _tk_available():
    """True only if a Tk root window can really be created on this machine."""
    try:
        import tkinter
    except Exception:
        return False
    try:
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


TK_AVAILABLE = _tk_available()
SKIP_REASON = "Tkinter/display not available (no _tkinter or no display)"

# Only import the GUI module when Tk works; importing it requires _tkinter.
if TK_AVAILABLE:
    import expenseTrackerGUI


@unittest.skipUnless(TK_AVAILABLE, SKIP_REASON)
class ModuleLevelTests(unittest.TestCase):
    """Things that don't need a live window."""

    def test_expense_types_list(self):
        self.assertEqual(len(expenseTrackerGUI.EXPENSE_TYPES), 22)
        self.assertIn("Housing", expenseTrackerGUI.EXPENSE_TYPES)
        self.assertIn("Others", expenseTrackerGUI.EXPENSE_TYPES)

    def test_load_expenses_reads_rows(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, newline=""
        ) as f:
            csv.writer(f).writerows([
                ["2025", "06", "15", "Food", "12.50", "lunch"],
                ["2025", "06", "16", "Housing", "20.00", ""],
            ])
            path = f.name
        try:
            with patch.object(expenseTrackerGUI, "CSV_PATH", path):
                rows = expenseTrackerGUI.load_expenses()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][3], "Food")
        finally:
            os.remove(path)

    def test_load_expenses_missing_file_returns_empty(self):
        with patch.object(expenseTrackerGUI, "CSV_PATH", "/no/such/file.csv"):
            self.assertEqual(expenseTrackerGUI.load_expenses(), [])


@unittest.skipUnless(TK_AVAILABLE, SKIP_REASON)
class DatePickerTests(unittest.TestCase):
    def setUp(self):
        import tkinter
        self.root = tkinter.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_prev_month_wraps_to_previous_year(self):
        picker = expenseTrackerGUI.DatePicker(
            self.root, initial=datetime(2026, 1, 15)
        )
        picker._prev_month()
        self.assertEqual((picker.year, picker.month), (2025, 12))
        picker.destroy()

    def test_next_month_wraps_to_next_year(self):
        picker = expenseTrackerGUI.DatePicker(
            self.root, initial=datetime(2026, 12, 10)
        )
        picker._next_month()
        self.assertEqual((picker.year, picker.month), (2027, 1))
        picker.destroy()

    def test_pick_reports_zero_padded_iso_date(self):
        picked = []
        picker = expenseTrackerGUI.DatePicker(
            self.root, initial=datetime(2026, 7, 1), on_pick=picked.append
        )
        picker._pick(5)
        self.assertEqual(picked, ["2026-07-05"])


@unittest.skipUnless(TK_AVAILABLE, SKIP_REASON)
class AppTests(unittest.TestCase):
    def setUp(self):
        # Route the app's CSV to a throwaway temp file.
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self._patch = patch.object(expenseTrackerGUI, "CSV_PATH", self.csv_path)
        self._patch.start()
        self.app = expenseTrackerGUI.ExpenseTrackerApp()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self._patch.stop()
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def _read_rows(self):
        with open(self.csv_path, newline="") as f:
            return [row for row in csv.reader(f) if row]

    def test_add_expense_writes_row(self):
        self.app.amount_var.set("12.5")
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[2])
        self.app.date_var.set("2025-06-15")
        self.app.details_var.set("weekly shop")
        self.app._add_expense()

        rows = self._read_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0],
            ["2025", "06", "15", expenseTrackerGUI.EXPENSE_TYPES[2], "12.5", "weekly shop"],
        )
        # Fields are cleared after a successful add.
        self.assertEqual(self.app.amount_var.get(), "")

    def test_add_expense_rejects_missing_type(self):
        self.app.amount_var.set("10")
        self.app.category_var.set("")  # nothing selected
        self.app.date_var.set("2025-06-15")
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self._read_rows(), [])

    def test_add_expense_rejects_bad_amount(self):
        self.app.amount_var.set("-5")
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[0])
        self.app.date_var.set("2025-06-15")
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self._read_rows(), [])

    def test_refresh_summary_groups_and_keeps_details(self):
        with open(self.csv_path, "w", newline="") as f:
            csv.writer(f).writerows([
                ["2025", "06", "15", "Food", "12.50", "lunch"],
                ["2025", "07", "01", "Housing", "20.00", ""],
            ])
        self.app._refresh_summary()

        tree = self.app.summary_tree
        months = tree.get_children("")
        self.assertEqual(len(months), 2)  # two month groups

        # First child of the earliest month keeps its details value.
        first_month = months[0]
        child = tree.get_children(first_month)[0]
        category, details, amount = tree.item(child, "values")
        self.assertEqual(category, "Food")
        self.assertEqual(details, "lunch")

        self.assertIn("32.50", self.app.total_label.cget("text"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
