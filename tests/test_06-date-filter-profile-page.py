"""
Black-box tests for Spec 06: Date Filter for Profile Page
(.claude/specs/06-date-filter-profile-page.md)

These tests are derived from the spec's Routes / Database changes / Rules
for implementation / Definition of done sections, not from reading
app.py's implementation. Per the spec:

- GET /profile gains two optional, independent query-string parameters:
  `start` (inclusive lower bound) and `end` (inclusive upper bound), both
  ISO `YYYY-MM-DD` strings.
- Malformed/unparseable date values must be silently ignored (treated as
  absent), never causing a 500.
- The filter must scope summary stats, the transactions table, and the
  category breakdown identically, and must never leak another user's data.
- The date inputs must be pre-filled with the active filter values, and an
  "All Time" pill must always be visible, linking back to the unfiltered
  view (it doubles as the clear-filter control).
- No new schema/routes; auth guard (redirect to /login when logged out)
  is unchanged.

The seeded demo user (id=1, via database.db.seed_db()) has these expenses,
which the happy-path tests below rely on:

    1. 2026-07-01  Food           450.00
    2. 2026-07-02  Transport      120.00
    3. 2026-07-03  Bills         1500.00
    4. 2026-07-05  Health         800.00
    5. 2026-07-08  Entertainment  600.00
    6. 2026-07-12  Shopping      2200.00
    7. 2026-07-15  Other          250.00
    8. 2026-07-20  Food           350.00

All-time:               count=8  total=6270.00  top_category=Shopping
start=07-01, end=07-15: count=7  total=5920.00  top_category=Shopping
start=07-05 (no end):   count=5  total=4200.00  top_category=Shopping
end=07-05 (no start):   count=4  total=2870.00  top_category=Bills
start=07-20, end=07-01 (start after end, nonsensical -> treated as absent, all-time): count=8 total=6270.00
"""

import re

import pytest


def html(response):
    return response.get_data(as_text=True)


# --------------------------------------------------------------------- #
# Auth guard (unchanged from Step 5, must still hold with filter params) #
# --------------------------------------------------------------------- #

def test_profile_redirects_to_login_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.location


def test_profile_with_filter_params_still_redirects_when_logged_out(client):
    """Auth guard must apply before/regardless of date-filter parsing."""
    response = client.get("/profile?start=2026-07-01&end=2026-07-15")
    assert response.status_code == 302
    assert "/login" in response.location


# --------------------------------------------------------------------- #
# DOD: unfiltered /profile behaves exactly as before                     #
# --------------------------------------------------------------------- #

def test_profile_no_query_params_shows_all_time_data(logged_in_client):
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;6270.00" in body
    assert ">8<" in body or "8" in body  # transaction count
    assert "Shopping" in body
    # all 8 seeded transactions should be listed
    for date_str in (
        "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-05",
        "2026-07-08", "2026-07-12", "2026-07-15", "2026-07-20",
    ):
        assert date_str in body


# --------------------------------------------------------------------- #
# DOD: start + end together scopes stats/transactions/breakdown          #
# --------------------------------------------------------------------- #

def test_profile_filter_with_start_and_end_scopes_all_sections(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-01&end=2026-07-15")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;5920.00" in body, (
        "Summary stats total should be scoped to 2026-07-01..2026-07-15 "
        "(expected 5920.00 for 7 in-range expenses)"
    )
    # the out-of-range expense (2026-07-20, "Dinner with friends") must
    # not appear in the transaction history table
    assert "Dinner with friends" not in body
    assert "2026-07-20" not in body
    # an in-range expense must still be present
    assert "Miscellaneous" in body
    assert "2026-07-15" in body


# --------------------------------------------------------------------- #
# DOD: start only (no end) -> expenses on/after start                    #
# --------------------------------------------------------------------- #

def test_profile_filter_with_start_only(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-05")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;4200.00" in body, "Expected total 4200.00 for expenses on/after 2026-07-05"
    # expenses before 2026-07-05 must be excluded
    assert "Groceries for the week" not in body
    assert "Auto fare" not in body
    assert "Electricity bill" not in body
    # expenses on/after 2026-07-05 must be present
    assert "Pharmacy" in body
    assert "Dinner with friends" in body


# --------------------------------------------------------------------- #
# DOD: end only (no start) -> expenses on/before end                     #
# --------------------------------------------------------------------- #

def test_profile_filter_with_end_only(logged_in_client):
    response = logged_in_client.get("/profile?end=2026-07-05")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;2870.00" in body, "Expected total 2870.00 for expenses on/before 2026-07-05"
    assert "Pharmacy" in body  # 2026-07-05 itself is inclusive
    # expenses after 2026-07-05 must be excluded
    assert "Movie tickets" not in body
    assert "New shoes" not in body
    assert "Dinner with friends" not in body


# --------------------------------------------------------------------- #
# DOD: malformed date does not crash, behaves as if absent                #
# --------------------------------------------------------------------- #

def test_profile_malformed_start_does_not_crash(logged_in_client):
    response = logged_in_client.get("/profile?start=not-a-date")
    assert response.status_code == 200
    body = html(response)
    # treated as absent -> identical to the all-time view
    assert "&#8377;6270.00" in body


def test_profile_malformed_end_does_not_crash(logged_in_client):
    response = logged_in_client.get("/profile?end=banana")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;6270.00" in body


def test_profile_start_after_end_does_not_500(logged_in_client):
    """Rules: nonsensical ranges (start after end) must not raise a 500,
    and are treated as if the filter were absent entirely (all-time)."""
    response = logged_in_client.get("/profile?start=2026-07-20&end=2026-07-01")
    assert response.status_code == 200
    body = html(response)
    assert "&#8377;6270.00" in body


# --------------------------------------------------------------------- #
# DOD: date inputs are pre-filled with the active filter values           #
# --------------------------------------------------------------------- #

def test_profile_date_inputs_prefilled_with_active_filter(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-01&end=2026-07-15")
    assert response.status_code == 200
    body = html(response)
    assert re.search(r'name=["\']start["\'][^>]*value=["\']2026-07-01["\']', body) or \
        re.search(r'value=["\']2026-07-01["\'][^>]*name=["\']start["\']', body), (
        "Expected an input named 'start' pre-filled with 2026-07-01"
    )
    assert re.search(r'name=["\']end["\'][^>]*value=["\']2026-07-15["\']', body) or \
        re.search(r'value=["\']2026-07-15["\'][^>]*name=["\']end["\']', body), (
        "Expected an input named 'end' pre-filled with 2026-07-15"
    )


def test_profile_date_inputs_empty_when_no_filter(logged_in_client):
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    body = html(response)
    assert re.search(r'name=["\']start["\']', body), "Expected a date input named 'start'"
    assert re.search(r'name=["\']end["\']', body), "Expected a date input named 'end'"


# --------------------------------------------------------------------- #
# DOD: "All Time" pill always visible, clears filter, links to /profile   #
# --------------------------------------------------------------------- #

def test_profile_all_time_pill_visible_when_filter_active(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-01")
    assert response.status_code == 200
    body = html(response)
    assert "All Time" in body, "The 'All Time' pill should be visible when a filter is active"
    assert re.search(r'href=["\']/profile["\'][^>]*>\s*All Time', body), (
        "The 'All Time' pill should link back to the unfiltered /profile URL"
    )


def test_profile_all_time_pill_visible_when_no_filter_active(logged_in_client):
    response = logged_in_client.get("/profile")
    assert response.status_code == 200
    body = html(response)
    assert "All Time" in body, "The 'All Time' pill must always be visible"
    assert "filter-pill-active" in body, (
        "The 'All Time' pill should be highlighted as active on the unfiltered view"
    )


# --------------------------------------------------------------------- #
# DOD: filtering never leaks another user's expenses                      #
# --------------------------------------------------------------------- #

def test_profile_filter_does_not_expose_other_users_expenses(app_module):
    import database.db as db

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@spendly.com", "hashed"),
    )
    other_user_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (other_user_id, 9999.00, "Shopping", "2026-07-10", "Other user's secret expense"),
    )
    conn.commit()
    conn.close()

    with app_module.app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess["user_id"] = 1  # demo user, NOT other_user_id
            sess["user_name"] = "Demo User"

        response = test_client.get("/profile?start=2026-07-01&end=2026-07-15")
        assert response.status_code == 200
        body = html(response)
        assert "Other user's secret expense" not in body
        assert "9999.00" not in body


def test_profile_filter_scopes_correctly_for_second_user(app_module):
    """Same scenario from the other user's point of view: their own
    in-range expense shows, the demo user's expenses never appear."""
    import database.db as db

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other2@spendly.com", "hashed"),
    )
    other_user_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (other_user_id, 111.00, "Food", "2026-07-10", "Other user's lunch"),
    )
    conn.commit()
    conn.close()

    with app_module.app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess["user_id"] = other_user_id
            sess["user_name"] = "Other User"

        response = test_client.get("/profile?start=2026-07-01&end=2026-07-31")
        assert response.status_code == 200
        body = html(response)
        # apostrophe is HTML-escaped by Jinja autoescape ("&#39;")
        assert "Other user" in body and "lunch" in body
        # none of the demo user's seeded expenses should appear
        assert "Groceries for the week" not in body
        assert "Electricity bill" not in body


# --------------------------------------------------------------------- #
# Rules: no hex colours / no inline styles in the rendered markup         #
# --------------------------------------------------------------------- #

def test_profile_filter_markup_has_no_inline_styles(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-01&end=2026-07-15")
    assert response.status_code == 200
    body = html(response)
    assert "style=" not in body, "No inline styles are allowed per spec rules"


def test_profile_filter_markup_has_no_hardcoded_hex_colours(logged_in_client):
    response = logged_in_client.get("/profile?start=2026-07-01&end=2026-07-15")
    assert response.status_code == 200
    body = html(response)
    assert not re.search(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", body), (
        "No hardcoded hex colour values should appear in profile.html markup"
    )


# --------------------------------------------------------------------- #
# Rules: parameterised queries scope data correctly (direct unit tests)   #
# Exercised directly against the helper functions per the spec's         #
# "Database changes" section, independent of query-string parsing.       #
# --------------------------------------------------------------------- #

def test_get_summary_stats_scopes_by_date_range_directly(app_module):
    import database.db as db

    conn = db.get_db()
    stats = app_module._get_summary_stats(conn, 1, "2026-07-01", "2026-07-15")
    conn.close()
    assert stats["count"] == 7
    assert stats["total"] == pytest.approx(5920.00)
    assert stats["top_category"] == "Shopping"


def test_get_summary_stats_unfiltered_matches_all_time(app_module):
    import database.db as db

    conn = db.get_db()
    stats = app_module._get_summary_stats(conn, 1, None, None)
    conn.close()
    assert stats["count"] == 8
    assert stats["total"] == pytest.approx(6270.00)


def test_get_recent_transactions_scopes_by_date_range_directly(app_module):
    import database.db as db

    conn = db.get_db()
    rows = app_module._get_recent_transactions(conn, 1, "2026-07-05", None)
    conn.close()
    dates = [row["date"] for row in rows]
    assert "2026-07-01" not in dates
    assert "2026-07-02" not in dates
    assert "2026-07-03" not in dates
    assert "2026-07-05" in dates
    assert "2026-07-20" in dates


def test_get_category_breakdown_scopes_by_date_range_directly(app_module):
    import database.db as db

    conn = db.get_db()
    rows = app_module._get_category_breakdown(conn, 1, "2026-07-01", "2026-07-05")
    conn.close()
    categories = {row["category"]: row["total"] for row in rows}
    assert categories == {
        "Food": pytest.approx(450.00),
        "Transport": pytest.approx(120.00),
        "Bills": pytest.approx(1500.00),
        "Health": pytest.approx(800.00),
    }
    assert "Shopping" not in categories  # 2026-07-12, out of range


def test_get_category_breakdown_never_mixes_users(app_module):
    import database.db as db

    conn = db.get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Isolated User", "isolated@spendly.com", "hashed"),
    )
    isolated_user_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (isolated_user_id, 42.00, "Food", "2026-07-01", "Isolated user's snack"),
    )
    conn.commit()

    rows = app_module._get_category_breakdown(conn, 1, None, None)
    conn.close()
    categories = {row["category"]: row["total"] for row in rows}
    # demo user's Food total must be 800.00 (450 + 350), not inflated by
    # the isolated user's 42.00 expense
    assert categories["Food"] == pytest.approx(800.00)
