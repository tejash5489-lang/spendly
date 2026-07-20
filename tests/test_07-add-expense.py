"""
Black-box tests for Spec 07: Add Expense
(.claude/specs/07-add-expense.md)

These tests are derived from the spec's Routes / Database changes / Rules
for implementation / Definition of done sections, not from reading
app.py's implementation. Per the spec:

- `GET /expenses/add` and `POST /expenses/add` are both logged-in only;
  redirect to `/login` when `session["user_id"]` is absent.
- GET renders a form with amount, category (from CATEGORIES), date
  (defaulted to today), and an optional description field.
- POST validates server-side (never trusting HTML5 constraints alone):
    - amount must parse as a positive number
    - category must be one of CATEGORIES
    - date must parse as YYYY-MM-DD
    - description is optional and may be empty
  On failure: re-render add_expense.html with an inline error and the
  submitted values, no row inserted, no 500.
  On success: INSERT a new expenses row via a parameterised query, with
  user_id always taken from session["user_id"] (never from client input),
  then redirect (302) to /profile (PRG pattern).

The seeded demo user (id=1, via database.db.seed_db()) has 8 pre-existing
expenses; tests that care about exact row counts insert against a fresh
second user or compare counts before/after rather than asserting absolute
totals tied to the seed data.
"""

from datetime import date

import pytest


def html(response):
    return response.get_data(as_text=True)


def count_expenses(app_module, user_id=None):
    import database.db as db

    conn = db.get_db()
    if user_id is None:
        row = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
    conn.close()
    return row["count"]


# --------------------------------------------------------------------- #
# Auth guard                                                             #
# --------------------------------------------------------------------- #

def test_get_add_expense_redirects_to_login_when_logged_out(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.location


def test_post_add_expense_redirects_to_login_when_logged_out(client, app_module):
    before = count_expenses(app_module)
    response = client.post(
        "/expenses/add",
        data={
            "amount": "100",
            "category": "Food",
            "date": "2026-07-10",
            "description": "Should not be inserted",
        },
    )
    assert response.status_code == 302
    assert "/login" in response.location
    # logged-out POST must not insert anything
    assert count_expenses(app_module) == before


# --------------------------------------------------------------------- #
# GET renders the form (logged in)                                       #
# --------------------------------------------------------------------- #

def test_get_add_expense_shows_form_when_logged_in(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    assert response.status_code == 200
    body = html(response)
    assert '<form' in body
    assert 'name="amount"' in body
    assert 'name="category"' in body
    assert 'name="date"' in body
    assert 'name="description"' in body


def test_get_add_expense_category_options_from_categories_list(logged_in_client):
    from database.db import CATEGORIES

    response = logged_in_client.get("/expenses/add")
    assert response.status_code == 200
    body = html(response)
    for category in CATEGORIES:
        assert f'>{category}<' in body or f'value="{category}"' in body


def test_get_add_expense_date_defaults_to_today(logged_in_client):
    response = logged_in_client.get("/expenses/add")
    assert response.status_code == 200
    body = html(response)
    today = date.today().isoformat()
    assert f'value="{today}"' in body


# --------------------------------------------------------------------- #
# DOD: valid submission inserts a row and redirects to /profile (PRG)     #
# --------------------------------------------------------------------- #

def test_post_valid_expense_inserts_row_and_redirects_to_profile(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)

    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "250.50",
            "category": "Food",
            "date": "2026-07-18",
            "description": "Lunch with friends",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/profile") or "/profile" in response.location

    assert count_expenses(app_module, user_id=1) == before + 1

    import database.db as db

    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE description = ?", ("Lunch with friends",)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["user_id"] == 1
    assert row["amount"] == pytest.approx(250.50)
    assert row["category"] == "Food"
    assert row["date"] == "2026-07-18"


def test_post_valid_expense_appears_on_profile_page(logged_in_client):
    logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "999.99",
            "category": "Shopping",
            "date": "2026-07-19",
            "description": "New shoes for the run",
        },
        follow_redirects=True,
    )

    response = logged_in_client.get("/profile")
    body = html(response)
    assert "New shoes for the run" in body
    assert "2026-07-19" in body


def test_post_valid_expense_does_not_render_form_directly(logged_in_client):
    """PRG pattern: the successful POST response itself must be a redirect,
    not a 200 render of the add_expense form (which would allow a
    refresh-triggered resubmission)."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "42",
            "category": "Other",
            "date": "2026-07-11",
            "description": "",
        },
    )
    assert response.status_code == 302


# --------------------------------------------------------------------- #
# DOD: invalid amount (negative / zero / non-numeric) rejected            #
# --------------------------------------------------------------------- #

def test_post_negative_amount_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "-50",
            "category": "Food",
            "date": "2026-07-10",
            "description": "Bad amount",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before


def test_post_zero_amount_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "date": "2026-07-10",
            "description": "Zero amount",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before


def test_post_non_numeric_amount_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-07-10",
            "description": "Non numeric",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before
    # no 500 - the app must handle the ValueError from float() parsing
    assert response.status_code != 500


# --------------------------------------------------------------------- #
# DOD: invalid category rejected                                         #
# --------------------------------------------------------------------- #

def test_post_invalid_category_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "100",
            "category": "NotARealCategory",
            "date": "2026-07-10",
            "description": "Bad category",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before


# --------------------------------------------------------------------- #
# DOD: invalid / missing date rejected                                    #
# --------------------------------------------------------------------- #

def test_post_missing_date_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "100",
            "category": "Food",
            "date": "",
            "description": "No date",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before


def test_post_malformed_date_rejected_no_row_inserted(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "100",
            "category": "Food",
            "date": "18/07/2026",
            "description": "Wrong format",
        },
    )
    assert response.status_code == 200
    body = html(response)
    assert "error" in body.lower()
    assert count_expenses(app_module, user_id=1) == before


def test_post_nonexistent_date_rejected_no_row_inserted(logged_in_client, app_module):
    """e.g. 2026-02-30 is not a real calendar date."""
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "100",
            "category": "Food",
            "date": "2026-02-30",
            "description": "Invalid calendar date",
        },
    )
    assert response.status_code == 200
    assert count_expenses(app_module, user_id=1) == before


# --------------------------------------------------------------------- #
# DOD: error re-renders with the submitted values preserved               #
# --------------------------------------------------------------------- #

def test_post_validation_error_repopulates_submitted_values(logged_in_client):
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "-10",
            "category": "Health",
            "date": "2026-07-10",
            "description": "Keep me on error",
        },
    )
    assert response.status_code == 200
    body = html(response)
    # the category and description should be re-populated (not wiped)
    assert "Keep me on error" in body
    assert 'value="-10"' in body or "-10" in body


# --------------------------------------------------------------------- #
# DOD: description is optional                                           #
# --------------------------------------------------------------------- #

def test_post_without_description_succeeds(logged_in_client, app_module):
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "75",
            "category": "Transport",
            "date": "2026-07-17",
            "description": "",
        },
    )
    assert response.status_code == 302
    assert count_expenses(app_module, user_id=1) == before + 1

    import database.db as db

    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? AND date = ? AND category = ?",
        (1, "2026-07-17", "Transport"),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["description"] in (None, "")


def test_post_missing_description_field_entirely_succeeds(logged_in_client, app_module):
    """Description omitted from the form data altogether (not just blank)."""
    before = count_expenses(app_module, user_id=1)
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "amount": "60",
            "category": "Bills",
            "date": "2026-07-16",
        },
    )
    assert response.status_code == 302
    assert count_expenses(app_module, user_id=1) == before + 1


# --------------------------------------------------------------------- #
# Rules: user_id always comes from session, never client input            #
# --------------------------------------------------------------------- #

def test_inserted_row_user_id_comes_from_session_not_client_input(logged_in_client, app_module):
    """Even if a malicious client stuffs a `user_id` field into the POST
    body, the inserted row must be tied to the session's user, never to
    whatever the client tried to inject."""
    response = logged_in_client.post(
        "/expenses/add",
        data={
            "user_id": "999999",
            "amount": "88",
            "category": "Entertainment",
            "date": "2026-07-14",
            "description": "Injected user_id attempt",
        },
    )
    assert response.status_code == 302

    import database.db as db

    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE description = ?", ("Injected user_id attempt",)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["user_id"] == 1  # the logged-in session user, not 999999
    assert row["user_id"] != 999999


def test_expense_added_by_one_user_is_isolated_from_another(app_module):
    """A second user's added expense must never be attributable to, or
    visible under, the first user's account."""
    import database.db as db

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Second User", "second@spendly.com", "hashed"),
    )
    second_user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    with app_module.app.test_client() as second_client:
        with second_client.session_transaction() as sess:
            sess["user_id"] = second_user_id
            sess["user_name"] = "Second User"

        response = second_client.post(
            "/expenses/add",
            data={
                "amount": "321",
                "category": "Other",
                "date": "2026-07-13",
                "description": "Second user's own expense",
            },
        )
        assert response.status_code == 302

    conn = db.get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE description = ?",
        ("Second user's own expense",),
    ).fetchone()
    demo_user_count = conn.execute(
        "SELECT COUNT(*) AS count FROM expenses WHERE user_id = 1 AND description = ?",
        ("Second user's own expense",),
    ).fetchone()["count"]
    conn.close()

    assert row is not None
    assert row["user_id"] == second_user_id
    assert demo_user_count == 0
