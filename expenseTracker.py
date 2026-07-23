"""Expense Tracker — console version.

A menu-driven command-line front end. All domain logic and persistence live in
``expense_store``; this module only deals with console input and output.
"""

import matplotlib.pyplot as plt

from chart import plot_monthly_totals
from expense_store import (
    EXPENSE_TYPES,
    Expense,
    ExpenseStore,
    group_by_month,
    monthly_totals,
    parse_date,
    total,
)


def positiveAmountCheck():
    while True:
        raw = input("Enter the amount used: ")
        try:
            amount = float(raw)
        except ValueError:
            print("The amount must be a number! Try again.")
            continue
        if amount > 0:
            return amount
        print("The amount must be a positive number! Try again.")


def selectExpenseType():
    print("Select an expense type:")
    for index, expenseType in enumerate(EXPENSE_TYPES, start=1):
        print(f"{index}. {expenseType}")

    while True:
        choice = input(f"Enter a number (1-{len(EXPENSE_TYPES)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(EXPENSE_TYPES):
            return EXPENSE_TYPES[int(choice) - 1]
        print("Invalid choice! Please pick a number from the list.")


def readDate():
    """Prompt until a valid date (or 'today') is entered; return (year, month, day)."""
    while True:
        raw = input('Enter the date in "YYYY-MM-DD" or "today": ')
        try:
            return parse_date(raw)
        except ValueError:
            print('Invalid date! Use the format "YYYY-MM-DD" or "today".')


def addExpense(store):
    amount = positiveAmountCheck()
    category = selectExpenseType()
    details = input("Enter details (optional, press Enter to skip): ").strip()
    year, month, day = readDate()

    store.add(Expense(year, month, day, category, amount, details))

    print("Expense added!")
    print("--------------------------------\n")


def viewSummary(store):
    expenses = store.load()

    if not expenses:
        print("No expenses recorded yet.\n")
        return

    print(f"Your total expense is {total(expenses): .2f}\n")
    print("Breakdown (grouped by month, oldest to latest):")

    for group in group_by_month(expenses):
        print(f"\n{group.month_key} (subtotal: {group.subtotal:.2f})")
        for expense in group.expenses:
            line = f"  {expense.iso_date}  {expense.category}: {expense.amount:.2f}"
            if expense.details:
                line += f" — {expense.details}"
            print(line)

    print("--------------------------------\n")


def produceGraph(store):
    totals = monthly_totals(store.load())

    if not totals:
        print("No expenses to graph yet.\n")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    plot_monthly_totals(ax, totals)
    fig.tight_layout()
    plt.show()


def main():
    store = ExpenseStore()

    operation = True
    while operation:
        print("1. Add an expense")
        print("2. View Summary")
        print("3. Produce Graph: Spending Trend")
        print("4. Exit")

        choice = input("Choose an option:")

        if choice == '1':
            addExpense(store)
        elif choice == '2':
            viewSummary(store)
        elif choice == '3':
            produceGraph(store)
        elif choice == '4':
            operation = False
        else:
            print("Invalid input! Please try again.\n")


if __name__ == "__main__":
    main()
