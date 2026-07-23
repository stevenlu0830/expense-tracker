"""Expense Tracker — GUI version.

A Tkinter front end for the CLI expense tracker. Same features:
  1. Add an expense
  2. View summary (total + breakdown)
  3. Produce monthly report (filter by year/month)
  4. Produce graph: spending trend (embedded matplotlib chart)

Shares the same expenses.csv (columns: year, month, day, category, amount)
as the CLI version, so data stays compatible between the two.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox

import matplotlib
matplotlib.use("TkAgg")  # render inside the Tk window
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Keep the CSV next to this script so the working directory doesn't matter.
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")


def load_expenses():
    """Return the CSV rows as a list of [year, month, day, category, amount]."""
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", newline="") as file:
        return [row for row in csv.reader(file) if row]


class ExpenseTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker")
        self.geometry("760x560")
        self.minsize(640, 480)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_tab = ttk.Frame(notebook)
        self.summary_tab = ttk.Frame(notebook)
        self.monthly_tab = ttk.Frame(notebook)
        self.graph_tab = ttk.Frame(notebook)

        notebook.add(self.add_tab, text="Add Expense")
        notebook.add(self.summary_tab, text="Summary")
        notebook.add(self.monthly_tab, text="Monthly Report")
        notebook.add(self.graph_tab, text="Spending Trend")

        self._build_add_tab()
        self._build_summary_tab()
        self._build_monthly_tab()
        self._build_graph_tab()

        # Refresh views whenever the user switches to them.
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ---------------------------------------------------------------- Add tab
    def _build_add_tab(self):
        frame = ttk.Frame(self.add_tab, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Amount ($):").grid(row=0, column=0, sticky="w", pady=6)
        self.amount_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.amount_var, width=30).grid(
            row=0, column=1, sticky="w", pady=6
        )

        ttk.Label(frame, text="Category:").grid(row=1, column=0, sticky="w", pady=6)
        self.category_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.category_var, width=30).grid(
            row=1, column=1, sticky="w", pady=6
        )

        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self.date_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.date_var, width=30).grid(
            row=2, column=1, sticky="w", pady=6
        )
        ttk.Button(frame, text="Today", command=self._set_today).grid(
            row=2, column=2, sticky="w", padx=6
        )

        ttk.Button(frame, text="Add Expense", command=self._add_expense).grid(
            row=3, column=1, sticky="w", pady=18
        )

        self.add_status = ttk.Label(frame, text="", foreground="green")
        self.add_status.grid(row=4, column=0, columnspan=3, sticky="w")

    def _set_today(self):
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))

    def _add_expense(self):
        # Validate amount: must be a positive number.
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a number.")
            return
        if amount <= 0:
            messagebox.showerror("Invalid amount", "Amount must be a positive number.")
            return

        category = self.category_var.get().strip()
        if not category:
            messagebox.showerror("Missing category", "Please enter a category.")
            return

        raw_date = self.date_var.get().strip()
        if raw_date.lower() == "today" or raw_date == "":
            date = datetime.now()
        else:
            try:
                date = datetime.strptime(raw_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Invalid date", 'Use the format "YYYY-MM-DD" or click Today.'
                )
                return

        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")

        with open(CSV_PATH, "a", newline="") as file:
            csv.writer(file).writerow([year, month, day, category, amount])

        self.add_status.config(
            text=f"Added: {category} ${amount:.2f} on {year}-{month}-{day}"
        )
        self.amount_var.set("")
        self.category_var.set("")
        self.date_var.set("")

    # ------------------------------------------------------------ Summary tab
    def _build_summary_tab(self):
        frame = ttk.Frame(self.summary_tab, padding=15)
        frame.pack(fill="both", expand=True)

        self.total_label = ttk.Label(
            frame, text="Total expense: $0.00", font=("TkDefaultFont", 13, "bold")
        )
        self.total_label.pack(anchor="w", pady=(0, 10))

        columns = ("date", "category", "amount")
        self.summary_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.summary_tree.heading("date", text="Date")
        self.summary_tree.heading("category", text="Category")
        self.summary_tree.heading("amount", text="Amount ($)")
        self.summary_tree.column("amount", anchor="e", width=120)
        self.summary_tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(
            frame, orient="vertical", command=self.summary_tree.yview
        )
        self.summary_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    def _refresh_summary(self):
        self.summary_tree.delete(*self.summary_tree.get_children())
        expenses = load_expenses()
        total = 0.0
        for exp in expenses:
            try:
                year, month, day, category, amount = exp[0], exp[1], exp[2], exp[3], float(exp[4])
            except (IndexError, ValueError):
                continue
            total += amount
            self.summary_tree.insert(
                "", "end",
                values=(f"{year}-{month}-{day}", category, f"{amount:.2f}"),
            )
        self.total_label.config(text=f"Total expense: ${total:.2f}")

    # ------------------------------------------------------ Monthly report tab
    def _build_monthly_tab(self):
        frame = ttk.Frame(self.monthly_tab, padding=15)
        frame.pack(fill="both", expand=True)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="Year:").pack(side="left")
        self.report_year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Entry(controls, textvariable=self.report_year_var, width=8).pack(
            side="left", padx=(4, 12)
        )

        ttk.Label(controls, text="Month (1-12):").pack(side="left")
        self.report_month_var = tk.StringVar(value=str(datetime.now().month))
        ttk.Entry(controls, textvariable=self.report_month_var, width=6).pack(
            side="left", padx=(4, 12)
        )

        ttk.Button(controls, text="Generate", command=self._generate_report).pack(
            side="left"
        )

        self.monthly_total_label = ttk.Label(
            frame, text="", font=("TkDefaultFont", 12, "bold")
        )
        self.monthly_total_label.pack(anchor="w", pady=(0, 8))

        columns = ("date", "category", "amount")
        self.monthly_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.monthly_tree.heading("date", text="Date")
        self.monthly_tree.heading("category", text="Category")
        self.monthly_tree.heading("amount", text="Amount ($)")
        self.monthly_tree.column("amount", anchor="e", width=120)
        self.monthly_tree.pack(fill="both", expand=True)

    def _generate_report(self):
        try:
            target_year = int(self.report_year_var.get())
            target_month = int(self.report_month_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Year and month must be integers.")
            return
        if target_year <= 0 or not (1 <= target_month <= 12):
            messagebox.showerror(
                "Invalid input", "Year must be positive and month must be 1-12."
            )
            return

        target_year = str(target_year)
        target_month = str(target_month).zfill(2)

        self.monthly_tree.delete(*self.monthly_tree.get_children())
        monthly_total = 0.0
        for exp in load_expenses():
            try:
                year, month, day, category, amount = exp[0], exp[1], exp[2], exp[3], float(exp[4])
            except (IndexError, ValueError):
                continue
            if year == target_year and month == target_month:
                monthly_total += amount
                self.monthly_tree.insert(
                    "", "end",
                    values=(f"{year}-{month}-{day}", category, f"{amount:.2f}"),
                )

        self.monthly_total_label.config(
            text=f"{target_year}-{target_month} total: ${monthly_total:.2f}"
        )

    # -------------------------------------------------------------- Graph tab
    def _build_graph_tab(self):
        frame = ttk.Frame(self.graph_tab, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Button(frame, text="Refresh Graph", command=self._draw_graph).pack(
            anchor="w", pady=(0, 8)
        )

        self.figure = Figure(figsize=(8, 4.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_graph(self):
        monthly_totals = defaultdict(float)
        for exp in load_expenses():
            try:
                year, month, amount = exp[0], exp[1], float(exp[4])
            except (IndexError, ValueError):
                continue
            monthly_totals[f"{year}-{month}"] += amount

        self.ax.clear()
        if monthly_totals:
            keys = sorted(monthly_totals.keys())
            values = [monthly_totals[k] for k in keys]
            self.ax.plot(keys, values, marker="o", linestyle="-")
            self.ax.set_title("Monthly Spending")
            self.ax.set_xlabel("Month (Year-Month)")
            self.ax.set_ylabel("Total Amount ($)")
            self.ax.grid(True)
            self.ax.tick_params(axis="x", rotation=45)
        else:
            self.ax.text(
                0.5, 0.5, "No expenses to display",
                ha="center", va="center", transform=self.ax.transAxes,
            )
        self.figure.tight_layout()
        self.canvas.draw()

    # ---------------------------------------------------------------- helpers
    def _on_tab_changed(self, event):
        tab_text = event.widget.tab(event.widget.select(), "text")
        if tab_text == "Summary":
            self._refresh_summary()
        elif tab_text == "Spending Trend":
            self._draw_graph()


if __name__ == "__main__":
    ExpenseTrackerApp().mainloop()
