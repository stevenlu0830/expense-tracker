import csv
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt

def positiveAmountCheck():
    amount = float(input("Enter the amount used: "))
    while amount <= 0:
        amount = float(input("The amount must be a positive number! Try again: "))
    
    return amount

def positiveMonthCheck():
    month = input("Enter the month (1-12): ").strip()
    while int(month) <= 0:
        month = input("The month must be a positive integer! Try again: ").strip()
    
    return month

def positiveYearCheck():
    year = input("Enter the year: ")
    while int(year) <= 0:
        year = input("The year must be a positive integer! Try again: ").strip()
    
    return year

def addExpense():
    amount = positiveAmountCheck()
    category = input("Enter the related category: ")
    date = input("Enter the date in \"YYYY-MM-DD\" or \"today\": ")

    if date.lower() == "today":
        date = datetime.now().strftime("%Y-%m-%d")
    
    year = date[:4]
    month = date[5:7]
    day = date[8:10]

    with open('expenses.csv', "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([year, month, day, category, amount])

    print("Expenses added!")
    print("--------------------------------\n")


def viewSummary():
    try:
        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            expenses = list(reader)
        print("File loaded!\n")
    
        sumExpense = 0.00

        if expenses:
            for expense in expenses:
                sumExpense = sumExpense + float(expense[4])

        print(f"Your total expense is {sumExpense: .2f}\n")
        print("Breakdown:")

        if expenses:
            for expense in expenses:
                category = expense[3]
                amount = float(expense[4])
                print(f"{category}: {amount: .2f}")

        print("--------------------------------\n")

    except FileNotFoundError:
        print("Error: Cannot find expenses.csv!\n")
    

def monthlyReport():
    try:
        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            expenses = list(reader)
        print("File loaded!")
    
        targetYear = positiveYearCheck()
        targetMonth = positiveMonthCheck()
        targetMonth = targetMonth.zfill(2)

        monthlyExpense = 0.00
        print("")
        print(f"Breakdown: ")

        if expenses:
            for expense in expenses:
                year = expense[0]
                month = expense[1]
                day = expense[2]
                category = expense[3]
                amount = float(expense[4])

                if year == targetYear:
                    if month == targetMonth:
                        monthlyExpense = monthlyExpense + amount
                        print(f"{category}: {amount:.2f}, Bought in {day}-{month}-{year}")
        
        print("")
        print(f"Your expense that month is: {monthlyExpense: .2f}")
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
        print("3. Produce Monthly Report")
        print("4. Produce Graph: Spending Trend")
        print("5. Exit")

        choice = input("Choose an option:")

        if choice == '1':
            addExpense()
        elif choice == '2':
            viewSummary()
        elif choice == '3':
            monthlyReport()
        elif choice == '4':
            produceGraph()
        elif choice == '5':
            print("Bye bye!")
            operation = False
        else:
            print("Invalid input! Please try again.\n")


if __name__ == "__main__":
    main()
