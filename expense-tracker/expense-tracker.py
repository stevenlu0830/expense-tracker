import csv
from datetime import datetime

def addExpense():
    amount = float(input("Enter the amount used:"))
    category = input("Enter the related category:")
    date = input("Enter the date in \"DD-MM-YYYY\" or \"today\": ")

    if date.lower() == "today":
        date = datetime.now().strftime("%Y-%m-%d")

    with open('expenses.csv', "a", newline='') as file:
        writer = csv.writer(file)
        writer.writerow([date, category, amount])

    print("Expenses added!\n")

def viewSummary():
    print("View Summary\n")

def main():

    operation = True

    while operation:
        print("1. Add an expense")
        print("2. View Summary")
        print("3. Exit")

        choice = input("Choose an option:")

        if choice == '1':
            addExpense()
        elif choice == '2':
            viewSummary()
        elif choice == '3':
            print("Bye bye")
            operation = False
        else:
            print("Invalid input! Please try again.\n")



if __name__ == "__main__":
    main()
