import calendar
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import CATEGORIES, get_db, init_db, seed_db

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


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Logout — coming in Step 3"


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
    stats = _get_summary_stats(conn, user_id, start, end)
    breakdown = _get_category_breakdown(conn, user_id, start, end)

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        transactions=transactions,
        stats=stats,
        breakdown=breakdown,
        categories=CATEGORIES,
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


# Builds a `user_id = ? [AND date >= ?] [AND date <= ?]` clause with matching
# bound params — start/end only ever reach SQL through these `?` placeholders.
def _where_clause(user_id, start, end):
    clauses = ["user_id = ?"]
    params = [user_id]
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    return " AND ".join(clauses), params


# --- SUBAGENT 1: transaction history --------------------------------- #
def _get_recent_transactions(conn, user_id, start=None, end=None, limit=10):
    where, params = _where_clause(user_id, start, end)
    query = f"""
        SELECT date, description, category, amount
        FROM expenses
        WHERE {where}
        ORDER BY date DESC
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

    return {
        "total": totals["total"],
        "count": totals["count"],
        "top_category": top["category"] if top else None,
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


# --- TEMPORARY: dev-only login shortcut for manual browser testing --- #
# Not part of the spec — remove before this branch is considered done.
@app.route("/dev/login-as/<int:user_id>")
def dev_login_as(user_id):
    if not app.debug:
        return "Not available", 404

    conn = get_db()
    user = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if user is None:
        return f"No user with id {user_id}", 404

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
