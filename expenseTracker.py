import csv
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

# The fixed set of expense types the user must choose from when adding an expense.
EXPENSE_TYPES = [
    "Housing", "Utilities", "Groceries", "Dining out", "Transportation",
    "Shopping", "Health", "Insurance", "Personal care", "Entertainment",
    "Subscriptions", "Travel", "Gifts and donations", "Debt payments",
    "Savings and investments", "Taxes", "Fees", "Education",
    "Childcare and kids", "Pets", "Business or work", "Others",
]

def positiveAmountCheck():
    amount = float(input("Enter the amount used: "))
    while amount <= 0:
        amount = float(input("The amount must be a positive number! Try again: "))

    return amount

def selectExpenseType():
    print("Select an expense type:")
    for index, expenseType in enumerate(EXPENSE_TYPES, start=1):
        print(f"{index}. {expenseType}")

    while True:
        choice = input(f"Enter a number (1-{len(EXPENSE_TYPES)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(EXPENSE_TYPES):
            return EXPENSE_TYPES[int(choice) - 1]
        print("Invalid choice! Please pick a number from the list.")

def addExpense():
    amount = positiveAmountCheck()
    category = selectExpenseType()
    details = input("Enter details (optional, press Enter to skip): ").strip()
    date = input("Enter the date in \"YYYY-MM-DD\" or \"today\": ")

    if date.lower() == "today":
        date = datetime.now().strftime("%Y-%m-%d")
    
    year = date[:4]
    month = date[5:7]
    day = date[8:10]

    with open('expenses.csv', "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([year, month, day, category, amount, details])

    print("Expenses added!")
    print("--------------------------------\n")


def viewSummary():
    try:
        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            expenses = [row for row in reader if row]
        print("File loaded!\n")

        sumExpense = 0.00
        groups = defaultdict(list)

        for expense in expenses:
            year, month, day = expense[0], expense[1], expense[2]
            category = expense[3]
            amount = float(expense[4])
            details = expense[5] if len(expense) > 5 else ""
            sumExpense = sumExpense + amount
            groups[f"{year}-{month}"].append((day, category, amount, details))

        print(f"Your total expense is {sumExpense: .2f}\n")
        print("Breakdown (grouped by month, oldest to latest):")

        # Groups sorted oldest to latest; expenses within each sorted by day.
        for yearMonth in sorted(groups):
            entries = sorted(groups[yearMonth], key=lambda e: e[0])
            subtotal = sum(amount for day, category, amount, details in entries)
            print(f"\n{yearMonth} (subtotal: {subtotal:.2f})")
            for day, category, amount, details in entries:
                line = f"  {yearMonth}-{day}  {category}: {amount:.2f}"
                if details:
                    line += f" — {details}"
                print(line)

        print("--------------------------------\n")

    except FileNotFoundError:
        print("Error: Cannot find expenses.csv!\n")
    

def produceGraph():
    try:
        dates = []
        amounts = []
        categories = []

        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            for row in reader:
                year, month, day, category, amount = row[0], row[1], row[2], row[3], row[4]
                dates.append(f"{year}-{month}")  
                amounts.append(float(amount))
                categories.append(category)
        print("File loaded!")
    
        monthly_totals = defaultdict(float)
        for date, amount in zip(dates, amounts):
            monthly_totals[date] += amount

        plt.figure(figsize=(10, 5))
        plt.plot(list(monthly_totals.keys()), list(monthly_totals.values()), marker='o', linestyle='-')
        plt.title("Monthly Spending")
        plt.xlabel("Month (Year-Month)")
        plt.ylabel("Total Amount ($)")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.show()

    except FileNotFoundError:
        print("Error: Cannot find expenses.csv!\n")


def main():

    operation = True
    while operation:
        print("1. Add an expense")
        print("2. View Summary")
        print("3. Produce Graph: Spending Trend")
        print("4. Exit")

        choice = input("Choose an option:")

        if choice == '1':
            addExpense()
        elif choice == '2':
            viewSummary()
        elif choice == '3':
            produceGraph()
        elif choice == '4':
            operation = False
        else:
            print("Invalid input! Please try again.\n")


if __name__ == "__main__":
    main()
