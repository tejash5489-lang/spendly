import calendar
import math
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    ACCOUNT_TYPES,
    CATEGORIES,
    INCOME_CATEGORIES,
    PAYMENT_METHODS,
    get_db,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template(
            "register.html", error="All fields are required.", name=name, email=email
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        )

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing is not None:
        conn.close()
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
        )

    password_hash = generate_password_hash(password)
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    error = "Invalid email or password."

    if not email or not password:
        return render_template("login.html", error=error, email=email)

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error=error, email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    if start and end and start > end:
        start = end = None

    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    presets = {
        "this_month": (this_month_start.isoformat(), today.isoformat()),
        "three_months": (_months_before(today, 3).isoformat(), today.isoformat()),
        "six_months": (_months_before(today, 6).isoformat(), today.isoformat()),
    }

    if not start and not end:
        active_preset = "all_time"
    else:
        active_preset = next(
            (key for key, value in presets.items() if value == (start, end)),
            None,
        )

    conn = get_db()
    user_id = session["user_id"]

    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    transactions = _get_recent_transactions(conn, user_id, start, end)
    income = _get_recent_income(conn, user_id, start, end)
    stats = _get_summary_stats(conn, user_id, start, end)
    breakdown = _get_category_breakdown(conn, user_id, start, end)
    accounts = _get_accounts(conn, user_id)

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        transactions=transactions,
        income=income,
        stats=stats,
        breakdown=breakdown,
        accounts=accounts,
        categories=CATEGORIES,
        income_categories=INCOME_CATEGORIES,
        start=start or "",
        end=end or "",
        presets=presets,
        active_preset=active_preset,
    )


@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("analytics.html")


def _parse_date(value):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.date().isoformat()


def _months_before(d, months):
    month = d.month - months
    year = d.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# Validates a submitted add-expense form. Returns (amount, error) where
# amount is a finite positive float on success, or (None, message) on failure.
def _validate_expense_form(form_values):
    amount = None
    try:
        amount = float(form_values["amount"])
    except ValueError:
        pass

    if amount is None or not math.isfinite(amount) or amount <= 0:
        return None, "Enter a valid amount greater than 0."
    if form_values["category"] not in CATEGORIES:
        return None, "Please select a valid category."
    if form_values["payment_method"] not in PAYMENT_METHODS:
        return None, "Please select a valid payment method."
    if not _parse_date(form_values["date"]):
        return None, "Please enter a valid date."

    return amount, None


# Validates a submitted add-income form. Returns (amount, error), mirroring
# _validate_expense_form but against INCOME_CATEGORIES and with no
# payment_method check (income has no payment-method concept).
def _validate_income_form(form_values):
    amount = None
    try:
        amount = float(form_values["amount"])
    except ValueError:
        pass

    if amount is None or not math.isfinite(amount) or amount <= 0:
        return None, "Enter a valid amount greater than 0."
    if form_values["category"] not in INCOME_CATEGORIES:
        return None, "Please select a valid category."
    if not _parse_date(form_values["date"]):
        return None, "Please enter a valid date."

    return amount, None


def _get_accounts(conn, user_id):
    return conn.execute(
        "SELECT id, name, type, balance FROM accounts WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()


NEW_ACCOUNT_OPTION = "__new__"


# Resolves a submitted account_id form value. Returns (account_id, error)
# where account_id is None if the field was left blank, or an int belonging
# to user_id on success. Any invalid/unowned value yields the same generic
# error, so a nonexistent id can't be distinguished from someone else's.
# If raw is NEW_ACCOUNT_OPTION, a fresh account is created from new_name /
# new_type (the "+ Add a new account" path on the expense/income forms) and
# its id is returned instead of resolving an existing one.
def _resolve_account_id(conn, user_id, raw, new_name="", new_type=""):
    raw = (raw or "").strip()
    if not raw:
        return None, None

    if raw == NEW_ACCOUNT_OPTION:
        new_name = (new_name or "").strip()
        new_type = (new_type or "").strip() or "Other"
        if not new_name:
            return None, "Please enter a name for the new account."
        account_id = conn.execute(
            "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, 0)",
            (user_id, new_name, new_type),
        ).lastrowid
        return account_id, None

    try:
        account_id = int(raw)
    except ValueError:
        return None, "Please select a valid account."

    owned = conn.execute(
        "SELECT id FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id)
    ).fetchone()
    if owned is None:
        return None, "Please select a valid account."

    return account_id, None


# Builds a `user_id = ? [AND date >= ?] [AND date <= ?]` clause with matching
# bound params — start/end only ever reach SQL through these `?` placeholders.
# `prefix` (e.g. "income.") qualifies each column for queries that JOIN
# another table also having a user_id column, to avoid an ambiguous-column
# error — existing single-table callers leave it as "".
def _where_clause(user_id, start, end, prefix=""):
    clauses = [f"{prefix}user_id = ?"]
    params = [user_id]
    if start:
        clauses.append(f"{prefix}date >= ?")
        params.append(start)
    if end:
        clauses.append(f"{prefix}date <= ?")
        params.append(end)
    return " AND ".join(clauses), params


# --- SUBAGENT 1: transaction history --------------------------------- #
def _get_recent_transactions(conn, user_id, start=None, end=None, limit=10):
    where, params = _where_clause(user_id, start, end, prefix="expenses.")
    query = f"""
        SELECT expenses.id, expenses.date, expenses.description, expenses.category,
               expenses.amount, expenses.payment_method, accounts.name AS account_name
        FROM expenses
        LEFT JOIN accounts ON expenses.account_id = accounts.id
        WHERE {where}
        ORDER BY expenses.date DESC
        LIMIT ?
        """
    return conn.execute(query, params + [limit]).fetchall()


def _get_recent_income(conn, user_id, start=None, end=None, limit=10):
    where, params = _where_clause(user_id, start, end, prefix="income.")
    query = f"""
        SELECT income.id, income.date, income.description, income.category,
               income.amount, accounts.name AS account_name
        FROM income
        JOIN accounts ON income.account_id = accounts.id
        WHERE {where}
        ORDER BY income.date DESC
        LIMIT ?
        """
    return conn.execute(query, params + [limit]).fetchall()


# --- SUBAGENT 2: summary stats ---------------------------------------- #
def _get_summary_stats(conn, user_id, start=None, end=None):
    where, params = _where_clause(user_id, start, end)

    totals_query = f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE {where}
        """
    totals = conn.execute(totals_query, params).fetchone()

    top_query = f"""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE {where}
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
        """
    top = conn.execute(top_query, params).fetchone()

    income_total = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total FROM income WHERE {where}", params
    ).fetchone()["total"]

    return {
        "total": totals["total"],
        "count": totals["count"],
        "top_category": top["category"] if top else None,
        "total_income": income_total,
        "net_balance": income_total - totals["total"],
    }


# --- SUBAGENT 3: category breakdown ------------------------------------ #
def _get_category_breakdown(conn, user_id, start=None, end=None):
    where, params = _where_clause(user_id, start, end)
    query = f"""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE {where}
        GROUP BY category
        ORDER BY total DESC
        """
    return conn.execute(query, params).fetchall()


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    today = date.today().isoformat()
    form_values = {
        "amount": "",
        "category": "",
        "payment_method": "",
        "account_id": "",
        "new_account_name": "",
        "new_account_type": "",
        "date": today,
        "description": "",
    }
    error = None

    conn = get_db()

    if request.method == "POST":
        form_values["amount"] = request.form.get("amount", "")
        form_values["category"] = request.form.get("category", "")
        form_values["payment_method"] = request.form.get("payment_method", "")
        form_values["account_id"] = request.form.get("account_id", "")
        form_values["new_account_name"] = request.form.get("new_account_name", "")
        form_values["new_account_type"] = request.form.get("new_account_type", "")
        form_values["date"] = request.form.get("date", "")
        form_values["description"] = request.form.get("description", "").strip()

        amount, error = _validate_expense_form(form_values)

        account_id = None
        if error is None:
            account_id, error = _resolve_account_id(
                conn,
                session["user_id"],
                form_values["account_id"],
                form_values["new_account_name"],
                form_values["new_account_type"],
            )

        if error is None:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, payment_method, date, description, account_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    amount,
                    form_values["category"],
                    form_values["payment_method"],
                    form_values["date"],
                    form_values["description"] or None,
                    account_id,
                ),
            )
            if account_id is not None:
                conn.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, session["user_id"]),
                )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))

    accounts = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        account_types=ACCOUNT_TYPES,
        accounts=accounts,
        error=error,
        **form_values,
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    expense = conn.execute(
        "SELECT id, amount, category, payment_method, date, description, account_id "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()

    if expense is None:
        conn.close()
        return "Not found", 404

    form_values = {
        "amount": expense["amount"],
        "category": expense["category"],
        "payment_method": expense["payment_method"],
        "account_id": str(expense["account_id"]) if expense["account_id"] is not None else "",
        "date": expense["date"],
        "description": expense["description"] or "",
    }
    error = None

    if request.method == "POST":
        form_values["amount"] = request.form.get("amount", "")
        form_values["category"] = request.form.get("category", "")
        form_values["payment_method"] = request.form.get("payment_method", "")
        form_values["account_id"] = request.form.get("account_id", "")
        form_values["date"] = request.form.get("date", "")
        form_values["description"] = request.form.get("description", "").strip()

        amount, error = _validate_expense_form(form_values)

        account_id = None
        if error is None:
            account_id, error = _resolve_account_id(conn, session["user_id"], form_values["account_id"])

        if error is None:
            old_account_id = expense["account_id"]
            old_amount = expense["amount"]

            conn.execute(
                "UPDATE expenses SET amount = ?, category = ?, payment_method = ?, date = ?, description = ?, "
                "account_id = ? WHERE id = ? AND user_id = ?",
                (
                    amount,
                    form_values["category"],
                    form_values["payment_method"],
                    form_values["date"],
                    form_values["description"] or None,
                    account_id,
                    id,
                    session["user_id"],
                ),
            )
            if old_account_id is not None:
                conn.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                    (old_amount, old_account_id, session["user_id"]),
                )
            if account_id is not None:
                conn.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (amount, account_id, session["user_id"]),
                )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))

    accounts = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "edit_expense.html",
        id=id,
        categories=CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        accounts=accounts,
        error=error,
        **form_values,
    )


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    expense = conn.execute(
        "SELECT id, amount, account_id FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()

    if expense is None:
        conn.close()
        return "Not found", 404

    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    if expense["account_id"] is not None:
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
            (expense["amount"], expense["account_id"], session["user_id"]),
        )
    conn.commit()
    conn.close()
    return redirect(url_for("profile"))


@app.route("/income/add", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    today = date.today().isoformat()
    form_values = {
        "amount": "",
        "category": "",
        "account_id": "",
        "new_account_name": "",
        "new_account_type": "",
        "date": today,
        "description": "",
    }
    error = None

    conn = get_db()

    if request.method == "POST":
        form_values["amount"] = request.form.get("amount", "")
        form_values["category"] = request.form.get("category", "")
        form_values["account_id"] = request.form.get("account_id", "")
        form_values["new_account_name"] = request.form.get("new_account_name", "")
        form_values["new_account_type"] = request.form.get("new_account_type", "")
        form_values["date"] = request.form.get("date", "")
        form_values["description"] = request.form.get("description", "").strip()

        amount, error = _validate_income_form(form_values)

        account_id = None
        if error is None and not form_values["account_id"].strip():
            error = "Please select an account."
        if error is None:
            account_id, error = _resolve_account_id(
                conn,
                session["user_id"],
                form_values["account_id"],
                form_values["new_account_name"],
                form_values["new_account_type"],
            )

        if error is None:
            conn.execute(
                "INSERT INTO income (user_id, amount, category, date, description, account_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    amount,
                    form_values["category"],
                    form_values["date"],
                    form_values["description"] or None,
                    account_id,
                ),
            )
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                (amount, account_id, session["user_id"]),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))

    accounts = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "add_income.html",
        income_categories=INCOME_CATEGORIES,
        account_types=ACCOUNT_TYPES,
        accounts=accounts,
        error=error,
        **form_values,
    )


@app.route("/income/<int:id>/edit", methods=["GET", "POST"])
def edit_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    income_row = conn.execute(
        "SELECT id, amount, category, date, description, account_id "
        "FROM income WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()

    if income_row is None:
        conn.close()
        return "Not found", 404

    form_values = {
        "amount": income_row["amount"],
        "category": income_row["category"],
        "account_id": str(income_row["account_id"]),
        "date": income_row["date"],
        "description": income_row["description"] or "",
    }
    error = None

    if request.method == "POST":
        form_values["amount"] = request.form.get("amount", "")
        form_values["category"] = request.form.get("category", "")
        form_values["account_id"] = request.form.get("account_id", "")
        form_values["date"] = request.form.get("date", "")
        form_values["description"] = request.form.get("description", "").strip()

        amount, error = _validate_income_form(form_values)

        account_id = None
        if error is None and not form_values["account_id"].strip():
            error = "Please select an account."
        if error is None:
            account_id, error = _resolve_account_id(conn, session["user_id"], form_values["account_id"])

        if error is None:
            old_account_id = income_row["account_id"]
            old_amount = income_row["amount"]

            conn.execute(
                "UPDATE income SET amount = ?, category = ?, date = ?, description = ?, account_id = ? "
                "WHERE id = ? AND user_id = ?",
                (
                    amount,
                    form_values["category"],
                    form_values["date"],
                    form_values["description"] or None,
                    account_id,
                    id,
                    session["user_id"],
                ),
            )
            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                (old_amount, old_account_id, session["user_id"]),
            )
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
                (amount, account_id, session["user_id"]),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("profile"))

    accounts = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "edit_income.html",
        id=id,
        income_categories=INCOME_CATEGORIES,
        accounts=accounts,
        error=error,
        **form_values,
    )


@app.route("/income/<int:id>/delete", methods=["POST"])
def delete_income(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    income_row = conn.execute(
        "SELECT id, amount, account_id FROM income WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()

    if income_row is None:
        conn.close()
        return "Not found", 404

    conn.execute(
        "DELETE FROM income WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    )
    conn.execute(
        "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
        (income_row["amount"], income_row["account_id"], session["user_id"]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("profile"))


@app.route("/accounts", methods=["GET", "POST"])
def accounts():
    if "user_id" not in session:
        return redirect(url_for("login"))

    error = None
    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        type_ = request.form.get("type", "").strip()
        raw_balance = request.form.get("balance", "")

        balance = None
        try:
            balance = float(raw_balance)
        except ValueError:
            pass

        if not name:
            error = "Please enter an account name."
        elif not type_:
            error = "Please enter an account type."
        elif balance is None or not math.isfinite(balance):
            error = "Enter a valid starting balance."

        if error is None:
            conn.execute(
                "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
                (session["user_id"], name, type_, balance),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("accounts"))

    accounts_list = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "accounts.html",
        accounts=accounts_list,
        account_types=ACCOUNT_TYPES,
        error=error,
    )


@app.route("/accounts/<int:id>/add-funds", methods=["POST"])
def add_funds(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    account = conn.execute(
        "SELECT id FROM accounts WHERE id = ? AND user_id = ?", (id, session["user_id"])
    ).fetchone()

    if account is None:
        conn.close()
        return "Not found", 404

    error = None
    amount = None
    try:
        amount = float(request.form.get("amount", ""))
    except ValueError:
        pass

    if amount is None or not math.isfinite(amount) or amount <= 0:
        error = "Enter a valid amount greater than 0."

    if error is None:
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?",
            (amount, id, session["user_id"]),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("accounts"))

    accounts_list = _get_accounts(conn, session["user_id"])
    conn.close()
    return render_template(
        "accounts.html",
        accounts=accounts_list,
        account_types=ACCOUNT_TYPES,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
