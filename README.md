# Expense Tracker

A simple personal-finance app to log your daily expenses and understand where your
money goes. It comes in two flavours that share the same data:

- **Console version** (`expenseTracker.py`) — a menu-driven command-line tool.
- **GUI version** (`expenseTrackerGUI.py`) — a desktop window built with Tkinter.

Both read and write the same `expenses.csv` file, so you can switch between them freely.

## Features

- **Add an expense** — record an amount, a category (e.g. Food, Rent, Transport),
  and a date. Type a date as `YYYY-MM-DD` or use *today* for the current date.
  Amounts are validated to be positive numbers.
- **View summary** — see your **total spending** plus a breakdown **grouped by month**
  (ordered oldest to latest), with a **subtotal per month** and every expense sorted
  by date within its month.
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

## Data

Expenses are stored in `expenses.csv` in the project folder, one row per expense:

```
year,month,day,category,amount
2025,06,15,Food,12.50
```

The file is created automatically the first time you add an expense.
