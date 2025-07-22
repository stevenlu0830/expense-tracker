import csv
from datetime import datetime

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

def addExpense():
    amount = positiveAmountCheck()
    category = input("Enter the related category: ")
    date = input("Enter the date in \"YYYY-DD-MM\" or \"today\": ")

    if date.lower() == "today":
        date = datetime.now().strftime("%Y-%m-%d")

    with open('expenses.csv', "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([date, category, amount])

    print("Expenses added!\n")


def viewSummary():
    try:
        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            expenses = list(reader)
        print("File loaded!\n")
    
        sumExpense = 0.00

        if expenses:
            for expense in expenses:
                sumExpense = sumExpense + float(expense[2])

        print(f"Your total expense is {sumExpense: .2f}")
        print("Breakdown:")

        if expenses:
            for expense in expenses:
                category = expense[1]
                amount = float(expense[2])
                print(f"{category}: {amount: .2f}")

        print("\n")

    except FileNotFoundError:
        print("Error: Cannot find expenses.csv!\n")
    

def monthlyReport():
    try:
        with open("expenses.csv", "r") as file:
            reader = csv.reader(file)
            expenses = list(reader)
        print("File loaded!\n")
    
        targetYear = input("Enter the year: ")
        targetMonth = positiveMonthCheck()
        targetMonth = targetMonth.zfill(2)

        monthlyExpense = 0.00
        print(f"Breakdown: ")

        if expenses:
            for expense in expenses:
                date = expense[0]
                category = expense[1]
                amount = float(expense[2])

                if date[:4] == targetYear:
                    if date[5:7] == targetMonth:
                        monthlyExpense = monthlyExpense + amount
                        print(f"{category}: {amount:.2f}, Bought in {date}")
        
        print(f"Your expense that month is: {monthlyExpense}\n")

    except FileNotFoundError:
        print("Error: Cannot find expenses.csv!\n")


def main():

    operation = True

    while operation:
        print("1. Add an expense")
        print("2. View Summary")
        print("3. Month Report")
        print("4. Exit")

        choice = input("Choose an option:")

        if choice == '1':
            addExpense()
        elif choice == '2':
            viewSummary()
        elif choice == '3':
            monthlyReport()
        elif choice == '4':
            print("Bye bye")
            operation = False
        else:
            print("Invalid input! Please try again.\n")



if __name__ == "__main__":
    main()
