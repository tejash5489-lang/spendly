from flask import Flask, redirect, render_template, session, url_for

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

    conn = get_db()
    user_id = session["user_id"]

    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    transactions = _get_recent_transactions(conn, user_id)
    stats = _get_summary_stats(conn, user_id)
    breakdown = _get_category_breakdown(conn, user_id)

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        transactions=transactions,
        stats=stats,
        breakdown=breakdown,
        categories=CATEGORIES,
    )


# --- SUBAGENT 1: transaction history --------------------------------- #
def _get_recent_transactions(conn, user_id, limit=10):
    return conn.execute(
        """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


# --- SUBAGENT 2: summary stats ---------------------------------------- #
def _get_summary_stats(conn, user_id):
    totals = conn.execute(
        """
        SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    top = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    return {
        "total": totals["total"],
        "count": totals["count"],
        "top_category": top["category"] if top else None,
    }


# --- SUBAGENT 3: category breakdown ------------------------------------ #
def _get_category_breakdown(conn, user_id):
    return conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (user_id,),
    ).fetchall()


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
