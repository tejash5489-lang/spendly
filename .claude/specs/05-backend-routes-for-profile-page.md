Spec: Backend Routes for Profile Page

Overview
This feature replaces the `/profile` stub with a fully working profile page: a user info card, summary stats row, transaction history table, and category breakdown, all populated from real, parameterised SQL queries against the existing `users` and `expenses` tables. No hardcoded-UI interim step exists in this codebase, so this step builds the template and wires it to the database in one pass rather than converting a static mockup.

Depends on
Step 1: Database setup (`users`/`expenses` schema) — implemented on `main`.
Step 2: Registration (user accounts must be creatable) — not yet implemented on this branch; required so real users exist to view.
Step 3: Login + Logout (`session["user_id"]` must be set on login) — not yet implemented on this branch; `/profile` relies on this session key to identify and guard the current user.

Routes
GET /profile — render the profile page with the logged-in user's real data — logged-in only (redirect to /login if `session.get("user_id")` is absent)

Database changes
No database changes. The existing `users` and `expenses` tables are sufficient. Queries needed:
- User info: `SELECT name, email, created_at FROM users WHERE id = ?`
- Summary stats: `SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?`
- Top category: `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC LIMIT 1`
- Recent transactions: `SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 10`
- Category breakdown: `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC`

Templates
Create: `templates/profile.html` — full profile page extending `base.html`; contains four sections, all values passed in from real query results:
- User info card — avatar initials (derived from name), name, email, member-since date
- Summary stats row — total spent, number of transactions, top category
- Transaction history table — recent expenses with date, description, category badge, amount
- Category breakdown — per-category totals as a list or progress-bar rows

Modify: `templates/base.html` — when `session.get('user_id')` is set, add a "Profile" link (`{{ url_for('profile') }}`) in `.nav-links` alongside the logout link. No change to the logged-out nav state.

Files to change
`app.py` — replace the `/profile` stub with a real view function that:
- Redirects to `url_for("login")` if `"user_id" not in session`
- Calls `get_db()`, runs the queries listed above scoped to the session's `user_id`, closes the connection
- Renders `profile.html` with the user row, stats, top category, transactions, and category breakdown
`templates/base.html` — add the conditional "Profile" nav link described above.

Files to create
`templates/profile.html` as described above.

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL
Passwords hashed with werkzeug (no auth changes in this step)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
All data passed to `profile.html` must come from real parameterised queries — no hardcoded Python dicts/lists standing in for user or expense data
Category badges must use a CSS class, not inline colour styles
Do not implement expense add/edit/delete, registration, or login/logout logic in this step — scope is limited to the `/profile` route, its queries, and its template/nav link

Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The user info card shows the logged-in user's actual name, email, and formatted member-since date
- [ ] The summary stats row shows the correct total spent, transaction count, and top category computed from that user's real expenses
- [ ] The transaction history table lists that user's actual recent expenses only, not another user's
- [ ] The category breakdown shows correct per-category totals computed from that user's real expenses only
- [ ] No hardcoded stat/transaction data remains in `app.py` or `profile.html`
- [ ] No hex colour values appear in `profile.html` — only CSS variables
- [ ] The navbar shows a "Profile" link alongside "Logout" when logged in, and omits it when logged out
