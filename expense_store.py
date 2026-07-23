"""Shared domain + persistence layer for the Expense Tracker.

Both the console app (``expenseTracker.py``) and the GUI app
(``expenseTrackerGUI.py``) build on this module, so the expense-type list, the
CSV format/location, and the grouping/aggregation logic live in exactly one
place instead of being duplicated in each front end.

Responsibilities are kept separate:
  * :class:`Expense`      — the domain model for a single expense.
  * :class:`ExpenseStore` — persistence only (read/write the CSV file).
  * module-level functions (:func:`total`, :func:`group_by_month`,
    :func:`monthly_totals`) — pure aggregation over a list of expenses.

Keeping aggregation as pure functions means the front ends load the data once
and the logic can be unit-tested without any file or UI involved.
"""

import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

# Single source of truth for the selectable expense categories.
EXPENSE_TYPES = [
    "Housing", "Utilities", "Groceries", "Dining out", "Transportation",
    "Shopping", "Health", "Insurance", "Personal care", "Entertainment",
    "Subscriptions", "Travel", "Gifts and donations", "Debt payments",
    "Savings and investments", "Taxes", "Fees", "Education",
    "Childcare and kids", "Pets", "Business or work", "Others",
]

# The shared data file lives next to the code, independent of the working dir,
# so the console and GUI apps always read and write the same file.
DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "expenses.csv"
)


def parse_date(raw):
    """Turn a user-supplied date into ``(year, month, day)`` padded strings.

    Accepts ``"today"`` (case-insensitive) or an empty string for the current
    date, or an ISO ``"YYYY-MM-DD"`` string. Raises :class:`ValueError` on
    anything else (so callers can report the problem however they like).
    """
    raw = (raw or "").strip()
    if raw.lower() == "today" or raw == "":
        date = datetime.now()
    else:
        date = datetime.strptime(raw, "%Y-%m-%d")  # raises ValueError if malformed
    return date.strftime("%Y"), date.strftime("%m"), date.strftime("%d")


@dataclass
class Expense:
    """A single logged expense."""

    year: str
    month: str
    day: str
    category: str
    amount: float
    details: str = ""

    @property
    def month_key(self):
        """Grouping key, e.g. ``"2025-06"``."""
        return f"{self.year}-{self.month}"

    @property
    def iso_date(self):
        """Full date, e.g. ``"2025-06-15"``."""
        return f"{self.year}-{self.month}-{self.day}"

    @classmethod
    def from_row(cls, row):
        """Build an Expense from a raw CSV row.

        Raises :class:`ValueError` if the row is too short or the amount is not
        a number, letting the store skip unparseable rows instead of crashing.
        """
        if len(row) < 5:
            raise ValueError("expense row needs at least 5 columns")
        amount = float(row[4])  # raises ValueError on a bad number
        details = row[5] if len(row) > 5 else ""
        return cls(row[0], row[1], row[2], row[3], amount, details)

    def to_row(self):
        """Serialise back to the CSV column order."""
        return [self.year, self.month, self.day, self.category, self.amount, self.details]


@dataclass
class MonthGroup:
    """A month's expenses plus its subtotal, ready for display."""

    month_key: str
    expenses: list = field(default_factory=list)  # sorted by day, ascending
    subtotal: float = 0.0


class ExpenseStore:
    """Reads and writes :class:`Expense` records to a CSV file.

    The path is injectable so tests (and either front end) can point it at any
    file; it defaults to the shared :data:`DEFAULT_CSV_PATH`.
    """

    def __init__(self, path=DEFAULT_CSV_PATH):
        self.path = path

    def load(self):
        """Return all stored expenses (empty list if the file doesn't exist).

        Rows that can't be parsed are skipped rather than crashing the caller.
        """
        if not os.path.exists(self.path):
            return []
        expenses = []
        with open(self.path, "r", newline="") as file:
            for row in csv.reader(file):
                if not row:
                    continue
                try:
                    expenses.append(Expense.from_row(row))
                except ValueError:
                    continue
        return expenses

    def add(self, expense):
        """Append one expense to the CSV file, creating it if needed."""
        with open(self.path, "a", newline="") as file:
            csv.writer(file).writerow(expense.to_row())


def total(expenses):
    """Sum of the amounts across ``expenses``."""
    return sum(expense.amount for expense in expenses)


def group_by_month(expenses):
    """Group ``expenses`` into :class:`MonthGroup`s.

    Groups are ordered oldest to latest, and the expenses within each group are
    ordered by day (oldest to latest).
    """
    groups = defaultdict(list)
    for expense in expenses:
        groups[expense.month_key].append(expense)

    result = []
    for month_key in sorted(groups):
        entries = sorted(groups[month_key], key=lambda e: e.day)
        result.append(
            MonthGroup(month_key, entries, sum(e.amount for e in entries))
        )
    return result


def monthly_totals(expenses):
    """Return ``[(month_key, total), ...]`` ordered oldest to latest."""
    totals = defaultdict(float)
    for expense in expenses:
        totals[expense.month_key] += expense.amount
    return [(month_key, totals[month_key]) for month_key in sorted(totals)]
