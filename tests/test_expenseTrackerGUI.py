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
from types import SimpleNamespace
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

    def test_shift_month_within_the_same_year(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 5, 10))
        picker._next_month()
        self.assertEqual((picker.year, picker.month), (2026, 6))
        picker._prev_month()
        self.assertEqual((picker.year, picker.month), (2026, 5))
        picker.destroy()

    def test_pick_reports_zero_padded_iso_date(self):
        picked = []
        picker = expenseTrackerGUI.DatePicker(
            self.root, initial=datetime(2026, 7, 1), on_pick=picked.append
        )
        picker._pick(5)
        self.assertEqual(picked, ["2026-07-05"])

    def test_pick_without_callback_still_closes(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 7, 1))
        picker._pick(5)  # on_pick is None -> nothing reported, window still closes
        self.assertFalse(picker.winfo_exists())

    def test_header_change_to_new_month_redraws(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 3, 10))
        picker.month_combo.current(8)  # September
        picker._on_header_change()
        self.assertEqual((picker.year, picker.month), (2026, 9))
        picker.destroy()

    def test_header_change_to_new_year_redraws(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 3, 10))
        picker.year_spin.set(2030)
        picker._on_header_change()
        self.assertEqual((picker.year, picker.month), (2030, 3))
        picker.destroy()

    def test_header_change_keeps_current_year_when_spinbox_is_not_a_number(self):
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 3, 10))
        picker.year_spin.set("not-a-year")
        picker.month_combo.current(0)  # January, so the period really does change
        picker._on_header_change()
        self.assertEqual((picker.year, picker.month), (2026, 1))
        picker.destroy()

    def test_header_change_with_same_period_leaves_day_buttons_alone(self):
        # Guards the <FocusOut> case: rebuilding the grid here would destroy the
        # day button mid-click and silently drop the selection.
        picker = expenseTrackerGUI.DatePicker(self.root, initial=datetime(2026, 3, 10))
        before = [str(w) for w in picker.grid_frame.winfo_children()]
        picker._on_header_change()  # combo and spinbox still read March 2026
        after = [str(w) for w in picker.grid_frame.winfo_children()]
        self.assertEqual(after, before)
        picker.destroy()


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

    @property
    def notebook(self):
        """The ttk.Notebook holding the three tabs (it's each tab's master)."""
        return self.app.add_tab.master

    def _open_calendar_and_capture(self):
        self.app._open_calendar()
        pickers = [
            w for w in self.app.winfo_children()
            if isinstance(w, expenseTrackerGUI.DatePicker)
        ]
        self.assertEqual(len(pickers), 1)
        return pickers[0]

    def test_set_today_fills_in_todays_iso_date(self):
        self.app._set_today()
        self.assertEqual(self.app.date_var.get(), datetime.now().strftime("%Y-%m-%d"))

    def test_open_calendar_seeds_picker_from_the_typed_date(self):
        self.app.date_var.set(" 2026-09-04 ")  # padded: the handler strips it
        picker = self._open_calendar_and_capture()
        self.assertEqual((picker.year, picker.month), (2026, 9))
        picker.destroy()

    def test_open_calendar_falls_back_to_today_on_an_unparseable_date(self):
        self.app.date_var.set("04/09/2026")
        picker = self._open_calendar_and_capture()
        now = datetime.now()
        self.assertEqual((picker.year, picker.month), (now.year, now.month))
        picker.destroy()

    def test_open_calendar_writes_the_picked_day_back_to_the_date_field(self):
        self.app.date_var.set("2026-09-04")
        picker = self._open_calendar_and_capture()
        picker._pick(21)
        self.assertEqual(self.app.date_var.get(), "2026-09-21")

    def test_switching_to_summary_tab_refreshes_it(self):
        self.app.store.add(Expense("2025", "06", "15", "Food", 12.5))
        self.notebook.select(self.app.summary_tab)
        self.app._on_tab_changed(SimpleNamespace(widget=self.notebook))
        self.assertEqual(len(self.app.summary_tree.get_children("")), 1)

    def test_switching_to_trend_tab_redraws_the_graph(self):
        self.app.store.add(Expense("2025", "06", "15", "Food", 12.5))
        self.notebook.select(self.app.graph_tab)
        self.app._on_tab_changed(SimpleNamespace(widget=self.notebook))
        self.assertEqual(len(self.app.ax.lines), 1)

    def test_switching_to_add_tab_refreshes_nothing(self):
        self.app.store.add(Expense("2025", "06", "15", "Food", 12.5))
        self.notebook.select(self.app.add_tab)
        self.app._on_tab_changed(SimpleNamespace(widget=self.notebook))
        self.assertEqual(self.app.summary_tree.get_children(""), ())
        self.assertEqual(len(self.app.ax.lines), 0)

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
