"""Unit tests for the GUI front end (expenseTrackerGUI.py).

Tkinter needs its C extension (`_tkinter`) and a usable display. When either is
missing (e.g. a Python built without Tk, or a headless CI box), every test here
is skipped rather than failing — so importing the GUI module is done lazily,
only after we confirm a Tk root can actually be created.

Run from the project root with:
    python -m unittest discover -s tests -t . -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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

# Only import the GUI module (and its Tk deps) when Tk actually works.
if TK_AVAILABLE:
    import expenseTrackerGUI
    from expense_store import Expense, ExpenseStore


@unittest.skipUnless(TK_AVAILABLE, SKIP_REASON)
class DatePickerTests(unittest.TestCase):
    def setUp(self):
        import tkinter
        self.root = tkinter.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_prev_month_wraps_to_previous_year(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 1, 15))
        picker._prev_month()
        self.assertEqual((picker.year, picker.month), (2025, 12))
        picker.destroy()

    def test_next_month_wraps_to_next_year(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 12, 10))
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
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.remove(self.csv_path)
        # Inject a store pointed at a throwaway file (no monkeypatching needed).
        self.app = expenseTrackerGUI.ExpenseTrackerApp(store=ExpenseStore(self.csv_path))
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_add_expense_writes_row(self):
        self.app.amount_var.set("12.5")
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[2])
        self.app.date_var.set("2025-06-15")
        self.app.details_var.set("weekly shop")
        self.app._add_expense()

        loaded = self.app.store.load()
        self.assertEqual(len(loaded), 1)
        e = loaded[0]
        self.assertEqual(
            (e.iso_date, e.category, e.amount, e.details),
            ("2025-06-15", expenseTrackerGUI.EXPENSE_TYPES[2], 12.5, "weekly shop"),
        )
        self.assertEqual(self.app.amount_var.get(), "")  # cleared after add

    def test_add_expense_rejects_missing_type(self):
        self.app.amount_var.set("10")
        self.app.category_var.set("")
        self.app.date_var.set("2025-06-15")
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self.app.store.load(), [])

    def test_add_expense_rejects_non_positive_amount(self):
        self.app.amount_var.set("-5")
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[0])
        self.app.date_var.set("2025-06-15")
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self.app.store.load(), [])

    def test_add_expense_rejects_non_numeric_amount(self):
        self.app.amount_var.set("abc")  # exercises the float()/except ValueError branch
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[0])
        self.app.date_var.set("2025-06-15")
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self.app.store.load(), [])

    def test_add_expense_rejects_invalid_date(self):
        self.app.amount_var.set("10")
        self.app.category_var.set(expenseTrackerGUI.EXPENSE_TYPES[0])
        self.app.date_var.set("15/06/2025")  # not ISO -> parse_date raises
        with patch.object(expenseTrackerGUI.messagebox, "showerror") as err:
            self.app._add_expense()
        err.assert_called_once()
        self.assertEqual(self.app.store.load(), [])

    def test_refresh_summary_groups_subtotals_and_details(self):
        self.app.store.add(Expense("2025", "06", "15", "Food", 12.5, "lunch"))
        self.app.store.add(Expense("2025", "06", "20", "Food", 4.0))
        self.app.store.add(Expense("2025", "07", "01", "Housing", 20.0))
        self.app._refresh_summary()

        tree = self.app.summary_tree
        months = tree.get_children("")
        self.assertEqual(len(months), 2)

        # Month parent row shows that month's own subtotal (12.5 + 4.0), not the total.
        june_values = tree.item(months[0], "values")
        self.assertEqual(june_values[2], "16.50")

        child = tree.get_children(months[0])[0]
        category, details, amount = tree.item(child, "values")
        self.assertEqual((category, details), ("Food", "lunch"))
        self.assertIn("36.50", self.app.total_label.cget("text"))

    def test_draw_graph_with_data_plots_a_line(self):
        self.app.store.add(Expense("2025", "06", "15", "Food", 12.5))
        self.app.store.add(Expense("2025", "07", "01", "Housing", 20.0))
        self.app._draw_graph()
        self.assertEqual(len(self.app.ax.lines), 1)
        self.assertEqual(self.app.ax.get_title(), "Monthly Spending")

    def test_draw_graph_empty_shows_placeholder(self):
        self.app._draw_graph()
        self.assertEqual(len(self.app.ax.lines), 0)
        texts = [t.get_text() for t in self.app.ax.texts]
        self.assertIn("No expenses to display", texts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
