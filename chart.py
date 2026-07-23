"""Shared matplotlib helper for the spending-trend chart.

Both front ends draw the same monthly-spending line chart. Keeping the chart
styling here (rather than copy-pasted in each front end) means a label or style
tweak happens in one place. This module deliberately does *not* import
matplotlib or belong to ``expense_store`` — it operates on an ``Axes`` the
caller supplies, so the domain layer stays free of any plotting dependency and
each caller keeps control of its own show/draw step and empty-state handling.
"""


def plot_monthly_totals(ax, totals):
    """Draw the monthly-spending line chart onto the given matplotlib ``Axes``.

    ``totals`` is a list of ``(month_key, amount)`` ordered oldest to latest,
    as returned by :func:`expense_store.monthly_totals`. The caller is
    responsible for the empty case and for showing/redrawing the figure.
    """
    months = [month_key for month_key, _ in totals]
    amounts = [amount for _, amount in totals]

    ax.plot(months, amounts, marker="o", linestyle="-")
    ax.set_title("Monthly Spending")
    ax.set_xlabel("Month (Year-Month)")
    ax.set_ylabel("Total Amount ($)")
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
