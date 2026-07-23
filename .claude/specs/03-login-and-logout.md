Spec: Login and Logout

Overview
This feature implements user authentication for Spendly. It converts the `/login` stub into a functional `POST` handler that verifies credentials against the `users` table and starts a session, and it converts the `/logout` stub into a handler that clears that session. After this step, the app can distinguish logged-in users from guests using `session['user_id']` — the exact check already used by `/profile`, `/analytics`, and every `/expenses/*` route. No separate "welcome" page is introduced: `/profile` already serves as the logged-in landing page, so a successful login redirects straight there.

Depends on
Step 1: Database setup (`users` table, `get_db()`) — implemented on `main`.
Step 2: Registration (`users` rows with hashed passwords now get created via `/register`) — implemented on `main`.

Routes
- `GET /login` — render the login form — public (already implemented, unchanged)
- `POST /login` — verify credentials, start the session, redirect to `/profile` — public
- `GET /logout` — clear the session, redirect to `/login` — public (no login required to log out; matches the existing `<a href="{{ url_for('logout') }}">` nav link, which is a plain `GET` link, not a form)

Both `login()` methods are handled by the existing view (replace the GET-only stub at `app.py:71-73`). `logout()` replaces its placeholder-string stub (`app.py:90-92`).

Database changes
No schema changes. One query is required:
```sql
-- look up the account being signed into
SELECT id, name, password_hash FROM users WHERE email = ?
```

Templates
Create: none — `templates/login.html` already exists with the correct form (`email`, `password` fields, `method="POST" action="/login"`) and an `{% if error %}` block already wired up for inline error display.

Modify: none. The existing template's error-rendering and field markup already match this spec's needs — no template changes required.

Files to change
`app.py`:
- Replace the `login` stub with a real view handling `GET` (render form, unchanged) and `POST` (validate, verify, set session, redirect).
- Replace the `logout` stub with a real view that clears the session and redirects to `/`.
- Remove the temporary `/dev/login-as/<int:user_id>` shortcut (`app.py:263-277`) — it exists only because real login wasn't implemented yet, and its own comment marks it for removal once a feature branch legitimately completes this work. Real login now supersedes it.

Files to create
None.

New dependencies
No new dependencies. `werkzeug.security.check_password_hash` ships with werkzeug, already a dependency (its counterpart `generate_password_hash` is already imported in `app.py` for registration).

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including email
Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
`POST /login` validation, re-rendering `login.html` with an inline `error` and the submitted `email` (never re-populate the password field) on any failure:
  - `email` and `password` must both be non-empty after stripping — error: "Invalid email or password." (do not use a separate "fields required" message here — keep one generic error for every failure mode on this route, so a missing field can't be distinguished from a wrong password)
  - Look up the user by email; if no row matches, or `check_password_hash` fails against the stored hash, show the same generic error: "Invalid email or password." — never reveal which part (email vs password) was wrong
On success: set `session["user_id"]` (int) and `session["user_name"]` (str, the user's `name`) — this matches the existing convention already used by the temporary dev-login shortcut and by `tests/conftest.py`'s `logged_in_client` fixture. Then redirect to `url_for("profile")` (PRG pattern).
`logout()` must call `session.clear()` then redirect to `url_for("login")`. Safe to call when already logged out (no error if `session` has nothing to clear).
Do not add "remember me" tokens, password reset, or email verification — out of scope for this step
Do not add a separate `/welcome` page — `/profile` is the post-login destination

Definition of done
- [x] Visiting `/login` with `GET` still renders the form exactly as before (no regression)
- [x] Submitting valid credentials (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and `session["user_name"]` and redirects to `/profile`
- [x] Submitting a wrong password shows "Invalid email or password." and does not set the session
- [x] Submitting an email that doesn't exist shows the same generic "Invalid email or password." error (indistinguishable from a wrong-password response)
- [x] Submitting an empty email or password shows the same generic error
- [x] The rejected-submission form re-populates `email` but never re-populates `password`
- [x] Visiting `/logout` while logged in clears the session and redirects to `/login`
- [x] After logout, the nav bar shows "Sign in" / "Get started" again instead of "Profile" / "Analytics" / "Logout"
- [x] Visiting `/logout` while already logged out does not error, and still redirects to `/login`
- [x] `/profile`, `/analytics`, and `/expenses/*` routes redirect anonymous visitors to `/login` exactly as before (no regression from removing the dev-login shortcut)
- [x] `/dev/login-as/<id>` no longer exists (404 on any id)
- [x] No hex colour values appear in any touched code (no template changes expected, but the rule holds if any are touched)
