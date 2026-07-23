# Expense Tracker

A simple personal-finance app to log your daily expenses and understand where your
money goes. It comes in two flavours that share the same data:

- **Console version** (`expenseTracker.py`) — a menu-driven command-line tool.
- **GUI version** (`expenseTrackerGUI.py`) — a desktop window built with Tkinter.

Both read and write the same `expenses.csv` file, so you can switch between them freely.

## Features

- **Add an expense** — record an amount, choose an **expense type** from a fixed list
  (Housing, Groceries, Transportation, Entertainment, …), add optional free-text
  **details**, and set a date. Type a date as `YYYY-MM-DD`, use *today* for the current
  date, or — in the GUI — click **📅 Calendar** to pick a day after choosing the month
  and/or year. Amounts are validated to be positive numbers.
- **View summary** — see your **total spending** plus a breakdown **grouped by month**
  (ordered oldest to latest), with a **subtotal per month**, every expense sorted by
  date within its month, and its **details** shown alongside the amount.
  - In the GUI, month subtotals and individual expenses are shown in **different
    colours**, and each month starts **collapsed** so you can expand only the ones
    you care about.
- **Spending trend graph** — a line chart of your total spending per month, drawn
  with matplotlib. In the GUI it's embedded right in the window.

## Requirements

- Python 3
- [matplotlib](https://matplotlib.org/) (used for the spending-trend graph)
- **GUI only:** Tkinter. It ships with most Python installs, but the Homebrew
  Python on macOS needs it added separately (see below).

## Setup

Clone the repo and install the dependency in a virtual environment:

```bash
git clone https://github.com/stevenlu0830/expense-tracker.git
cd expense-tracker

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install matplotlib
```

## How to Use

### Console version

```bash
python expenseTracker.py
```

You'll get a menu — type the number for the action you want:

```
1. Add an expense
2. View Summary
3. Produce Graph: Spending Trend
4. Exit
```

### GUI version

```bash
python expenseTrackerGUI.py
```

A window opens with three tabs — **Add Expense**, **Summary**, and **Spending Trend**.
The Summary and graph refresh automatically when you switch to their tabs.

> **macOS (Homebrew Python):** if you see `ModuleNotFoundError: No module named '_tkinter'`,
> install Tk once with `brew install python-tk@3.13` (match the number to your Python
> version), then run the GUI again.

## Project structure

```
expense_store.py        Shared domain + persistence layer (single source of truth)
expenseTracker.py       Console front end (presentation only)
expenseTrackerGUI.py    Tkinter GUI front end (presentation only)
expenses.csv            Data file (shared by both front ends)
tests/                  Unit tests
```

Both front ends are thin: the expense-type list, the CSV format/location, and all
grouping/aggregation logic live only in **`expense_store.py`** (an `Expense` model,
an `ExpenseStore` that reads/writes the file, and pure `total` / `group_by_month` /
`monthly_totals` functions). The console and GUI just collect input and render
results, so they stay consistent by construction.

## Running the tests

From the project root:

```bash
python -m unittest discover -s tests -t .
```

The GUI tests skip automatically when Tkinter/display isn't available; the domain
and console tests always run.

## Data

Expenses are stored in `expenses.csv` in the project folder, one row per expense.
Columns are `year, month, day, category, amount, details` (details may be empty):

```
2025,06,15,Groceries,12.50,weekly shop
2025,06,16,Transportation,5.75,
```

The file is created automatically the first time you add an expense.
