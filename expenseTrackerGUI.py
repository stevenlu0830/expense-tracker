"""Expense Tracker — GUI version.

A Tkinter front end with three tabs, sharing all domain logic and data with the
console app via ``expense_store``:
  1. Add Expense    — pick a type, amount, date (typed or via a calendar), details
  2. Summary        — total + month-grouped breakdown (collapsible, colour-coded)
  3. Spending Trend — embedded matplotlib chart of monthly totals

This module is presentation only; reading/writing and aggregation live in
``expense_store``, so the GUI and console stay consistent by construction.
"""

import calendar
from datetime import datetime
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox

import matplotlib
matplotlib.use("TkAgg")  # render inside the Tk window
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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


class ExpenseTrackerApp(tk.Tk):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or ExpenseStore()
        self.title("Expense Tracker")
        self.geometry("760x560")
        self.minsize(640, 480)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_tab = ttk.Frame(notebook)
        self.summary_tab = ttk.Frame(notebook)
        self.graph_tab = ttk.Frame(notebook)

        notebook.add(self.add_tab, text="Add Expense")
        notebook.add(self.summary_tab, text="Summary")
        notebook.add(self.graph_tab, text="Spending Trend")

        self._build_add_tab()
        self._build_summary_tab()
        self._build_graph_tab()

        # Refresh views whenever the user switches to them.
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ---------------------------------------------------------------- Add tab
    def _build_add_tab(self):
        frame = ttk.Frame(self.add_tab, padding=20)
        frame.pack(fill="both", expand=True)

        # Expense type: must be chosen from the fixed list (read-only dropdown).
        ttk.Label(frame, text="Expense type:").grid(row=0, column=0, sticky="w", pady=6)
        self.category_var = tk.StringVar()
        ttk.Combobox(
            frame, textvariable=self.category_var, values=EXPENSE_TYPES,
            state="readonly", width=28,
        ).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(frame, text="Amount ($):").grid(row=1, column=0, sticky="w", pady=6)
        self.amount_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.amount_var, width=30).grid(
            row=1, column=1, sticky="w", pady=6
        )

        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self.date_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.date_var, width=30).grid(
            row=2, column=1, sticky="w", pady=6
        )
        date_buttons = ttk.Frame(frame)
        date_buttons.grid(row=2, column=2, sticky="w", padx=6)
        ttk.Button(date_buttons, text="📅 Calendar", command=self._open_calendar).pack(
            side="left"
        )
        ttk.Button(date_buttons, text="Today", command=self._set_today).pack(
            side="left", padx=(6, 0)
        )

        # Details: free-text and optional.
        ttk.Label(frame, text="Details (optional):").grid(
            row=3, column=0, sticky="w", pady=6
        )
        self.details_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.details_var, width=30).grid(
            row=3, column=1, sticky="w", pady=6
        )

        ttk.Button(frame, text="Add Expense", command=self._add_expense).grid(
            row=4, column=1, sticky="w", pady=18
        )

        self.add_status = ttk.Label(frame, text="", foreground="green")
        self.add_status.grid(row=5, column=0, columnspan=3, sticky="w")

    def _set_today(self):
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))

    def _open_calendar(self):
        # Seed the picker with whatever valid date is already typed, else today.
        try:
            initial = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d")
        except ValueError:
            initial = datetime.now()
        DatePicker(self, initial=initial, on_pick=self.date_var.set)

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
        if category not in EXPENSE_TYPES:
            messagebox.showerror(
                "Missing expense type", "Please select an expense type from the list."
            )
            return

        details = self.details_var.get().strip()

        try:
            year, month, day = parse_date(self.date_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid date", 'Use the format "YYYY-MM-DD" or click Today.'
            )
            return

        self.store.add(Expense(year, month, day, category, amount, details))

        self.add_status.config(
            text=f"Added: {category} ${amount:.2f} on {year}-{month}-{day}"
        )
        self.amount_var.set("")
        self.category_var.set("")
        self.date_var.set("")
        self.details_var.set("")

    # ------------------------------------------------------------ Summary tab
    def _build_summary_tab(self):
        frame = ttk.Frame(self.summary_tab, padding=15)
        frame.pack(fill="both", expand=True)

        self.total_label = ttk.Label(
            frame, text="Total expense: $0.00", font=("TkDefaultFont", 13, "bold")
        )
        self.total_label.pack(anchor="w", pady=(0, 10))

        # Tree hierarchy: each year-month is a parent row (with its subtotal),
        # expenses within it are children sorted oldest to latest.
        self.summary_tree = ttk.Treeview(
            frame, columns=("category", "details", "amount"), show="tree headings"
        )
        self.summary_tree.heading("#0", text="Date / Month")
        self.summary_tree.heading("category", text="Category")
        self.summary_tree.heading("details", text="Details")
        self.summary_tree.heading("amount", text="Amount ($)")
        self.summary_tree.column("#0", width=160)
        self.summary_tree.column("details", width=200)
        self.summary_tree.column("amount", anchor="e", width=110)
        # Distinct text colours: month subtotals vs. individual breakdown rows.
        self.summary_tree.tag_configure("month", foreground="#1a56db")
        self.summary_tree.tag_configure("entry", foreground="#15803d")
        self.summary_tree.pack(fill="both", expand=True, side="left")

        scroll = ttk.Scrollbar(
            frame, orient="vertical", command=self.summary_tree.yview
        )
        self.summary_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    def _refresh_summary(self):
        self.summary_tree.delete(*self.summary_tree.get_children())

        expenses = self.store.load()
        for group in group_by_month(expenses):
            parent = self.summary_tree.insert(
                "", "end", text=group.month_key,
                values=("", "", f"{group.subtotal:.2f}"),
                open=False, tags=("month",),
            )
            for expense in group.expenses:
                self.summary_tree.insert(
                    parent, "end",
                    text=expense.iso_date,
                    values=(expense.category, expense.details, f"{expense.amount:.2f}"),
                    tags=("entry",),
                )

        self.total_label.config(text=f"Total expense: ${total(expenses):.2f}")

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
        totals = monthly_totals(self.store.load())

        self.ax.clear()
        if totals:
            plot_monthly_totals(self.ax, totals)
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


class DatePicker(tk.Toplevel):
    """Modal calendar popup: pick a day after choosing month and/or year.

    Calls on_pick(date_string) with a "YYYY-MM-DD" string when a day is clicked.
    """

    def __init__(self, master, initial=None, on_pick=None):
        super().__init__(master)
        self.title("Select Date")
        self.resizable(False, False)
        self.on_pick = on_pick
        self.transient(master)
        self.grab_set()  # modal: block the main window until a day is chosen

        base = initial or datetime.now()
        self.year = base.year
        self.month = base.month

        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill="x")
        ttk.Button(header, text="◀", width=3, command=self._prev_month).pack(side="left")

        self.month_combo = ttk.Combobox(
            header, state="readonly", width=11, values=list(calendar.month_name)[1:]
        )
        self.month_combo.current(self.month - 1)
        self.month_combo.pack(side="left", padx=4)
        self.month_combo.bind("<<ComboboxSelected>>", lambda e: self._on_header_change())

        self.year_spin = ttk.Spinbox(
            header, from_=1900, to=2100, width=6, command=self._on_header_change
        )
        self.year_spin.set(self.year)
        self.year_spin.pack(side="left", padx=4)
        self.year_spin.bind("<Return>", lambda e: self._on_header_change())
        self.year_spin.bind("<FocusOut>", lambda e: self._on_header_change())

        ttk.Button(header, text="▶", width=3, command=self._next_month).pack(side="left")

        self.grid_frame = ttk.Frame(self, padding=8)
        self.grid_frame.pack()
        self._draw_calendar()

    def _on_header_change(self):
        month = self.month_combo.current() + 1
        try:
            year = int(self.year_spin.get())
        except ValueError:
            year = self.year

        # Only rebuild the grid when the period actually changed. Otherwise a
        # <FocusOut> fired by clicking a day button would destroy that button
        # mid-click and silently drop the selection.
        if (year, month) == (self.year, self.month):
            return
        self.year, self.month = year, month
        self._draw_calendar()

    def _shift_month(self, delta):
        month = self.month + delta
        year = self.year
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        self.month, self.year = month, year
        self.month_combo.current(self.month - 1)
        self.year_spin.set(self.year)
        self._draw_calendar()

    def _prev_month(self):
        self._shift_month(-1)

    def _next_month(self):
        self._shift_month(1)

    def _draw_calendar(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        for col, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ttk.Label(self.grid_frame, text=name, width=4, anchor="center").grid(
                row=0, column=col, padx=1, pady=1
            )

        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                ttk.Button(
                    self.grid_frame, text=str(day), width=4,
                    command=lambda d=day: self._pick(d),
                ).grid(row=row, column=col, padx=1, pady=1)

    def _pick(self, day):
        if self.on_pick:
            self.on_pick(f"{self.year:04d}-{self.month:02d}-{day:02d}")
        self.destroy()


if __name__ == "__main__":
    ExpenseTrackerApp().mainloop()
