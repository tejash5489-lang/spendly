Spec: Date Filter for Profile Page

Overview
This feature adds an optional date-range filter to the `/profile` page, letting a logged-in user narrow the summary stats, transaction history, and category breakdown to a specific window (e.g. "this month," a custom range) instead of always seeing all-time totals. It builds directly on Step 5's real, per-user queries — no new tables or routes, just optional query-string parameters that scope the existing SQL.

Depends on
Step 1: Database setup (`users`/`expenses` schema) — implemented on `main`.
Step 5: Backend routes for profile page (`/profile` renders real user/stats/transactions/breakdown data) — implemented on `main`.

Routes
No new routes. The existing `GET /profile` route is extended to accept two optional query-string parameters:
- `start` — ISO date string `YYYY-MM-DD`, inclusive lower bound
- `end` — ISO date string `YYYY-MM-DD`, inclusive upper bound
Both are optional and independent (either, both, or neither may be present). Access remains logged-in only (redirect to `/login` if `session.get("user_id")` is absent) — unchanged from Step 5.

Database changes
No schema changes. The existing `expenses.date` column (`TEXT`, `YYYY-MM-DD` format) is sufficient for range comparison via SQLite's lexicographic string comparison on ISO dates. Existing Step 5 queries gain an optional `AND date >= ?` / `AND date <= ?` clause, built conditionally so unfiltered requests behave exactly as before:
- Summary stats: `SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? [AND date >= ?] [AND date <= ?]`
- Top category: `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? [AND date >= ?] [AND date <= ?] GROUP BY category ORDER BY total DESC LIMIT 1`
- Recent transactions: `SELECT date, description, category, amount FROM expenses WHERE user_id = ? [AND date >= ?] [AND date <= ?] ORDER BY date DESC LIMIT 10`
- Category breakdown: `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? [AND date >= ?] [AND date <= ?] GROUP BY category ORDER BY total DESC`

Templates
Create: No new templates.

Modify: `templates/profile.html` — add a date-filter bar above "Recent Transactions":
- Preset pills — "All Time", "This Month", "Last 3 Months", "Last 6 Months" — each a link to `/profile` with the corresponding `start`/`end` (or neither, for "All Time") baked into the URL; the active preset is visually highlighted based on which one matches the current `start`/`end`. "All Time" doubles as the clear-filter control and is always visible.
- A custom-range form alongside the pills: two `<input type="date">` fields (`name="start"`, `name="end"`), pre-filled from the current `start`/`end` query params if present, with an "Apply" submit button (`method="get"`, `action="{{ url_for('profile') }}"`) so the filtered view is a shareable/bookmarkable URL
- Existing stats row, transaction table, and category breakdown sections are unchanged in structure — they simply render whatever filtered data the view passes in

Files to change
`app.py` — extend the `profile()` view and its three helper functions (`_get_recent_transactions`, `_get_summary_stats`, `_get_category_breakdown`) to:
- Read `start`/`end` from `request.args`
- Validate each as a `YYYY-MM-DD` string (via `datetime.strptime`); silently ignore a malformed value rather than erroring, treating it as absent
- Pass validated `start`/`end` through to each helper and append the corresponding parameterised `AND date >= ?` / `AND date <= ?` clauses only when present
- Pass `start`/`end` (the validated values, or empty strings) to `profile.html` so the form can re-populate itself
`templates/profile.html` — add the filter form described above.

Files to create
None.

New dependencies
No new dependencies. `datetime` is standard library.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including the date bounds
Passwords hashed with werkzeug (no auth changes in this step)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
Authentication guard unchanged: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
Malformed or nonsensical dates (e.g. `start` after `end`, unparseable strings) must not raise a 500 — treat invalid input as if the filter were absent for that bound
Do not implement expense add/edit/delete, registration, or login/logout logic in this step — scope is limited to filtering the existing `/profile` data by date

Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data, identical to current behavior
- [ ] Visiting `/profile?start=2026-07-01&end=2026-07-15` shows stats, transactions, and category breakdown scoped only to expenses in that range
- [ ] Visiting `/profile?start=2026-07-01` (no `end`) shows only expenses on or after that date
- [ ] Visiting `/profile?end=2026-07-15` (no `start`) shows only expenses on or before that date
- [ ] Visiting `/profile?start=not-a-date` does not crash — behaves as if `start` were absent
- [ ] The date inputs are pre-filled with the active `start`/`end` values after filtering
- [ ] An "All Time" pill is always visible and returns to the unfiltered view, clearing any active filter
- [ ] Filtering one user's data never exposes another user's expenses
- [ ] No hex colour values appear in the new filter markup — only CSS variables
