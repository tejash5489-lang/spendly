Spec: Registration

Overview
This feature implements the `POST /register` handler, replacing its current GET-only stub with real logic that creates a new user account. It is the first authentication step in the Spendly roadmap: it does not log the user in or start a session (that's Step 3 — Login and Logout) — a successful registration simply redirects to `/login` so the user can sign in with their new credentials.

Depends on
Step 1: Database setup (`users` table schema) — implemented on `main`.

Routes
- `GET /register` — render the registration form — public (already implemented, unchanged)
- `POST /register` — validate the submitted form, create the user, redirect to `/login` — public

Both methods are handled by the existing `register` view (replace the GET-only stub at `app.py:26-28`).

Database changes
No schema changes. The existing `users` table (`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) already has every column this feature needs. Two queries are required:
```sql
-- check for an existing account with this email
SELECT id FROM users WHERE email = ?

-- create the new user, password hashed by werkzeug before this point
INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)
```

Templates
Create: none — `templates/register.html` already exists with the correct form (`name`, `email`, `password` fields only — no `confirm_password`, `method="POST" action="/register"`) and an `{% if error %}` block already wired up for inline error display.

Modify: none. The existing template's error-rendering and field markup already match this spec's needs — no template changes required.

Files to change
`app.py` — replace the `register` stub with a real view handling `GET` (render form, unchanged) and `POST` (validate, hash password, insert user, redirect).

Files to create
None.

New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already available (werkzeug ships with Flask) and already used in `database/db.py`'s `seed_db()`. `app.secret_key` is already set in `app.py` — no change needed there.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including name/email/password_hash
Passwords hashed with werkzeug (`generate_password_hash`) — never store or log a plaintext password
Use CSS variables — never hardcode hex values
All templates extend `base.html` (no template changes needed here, but if touched, must still extend `base.html`)
No inline styles
Validation, in order, re-rendering `register.html` with an inline `error` and the submitted `name`/`email` (never re-populate the password field) on any failure:
  - `name`, `email`, and `password` must all be non-empty after stripping whitespace — error: "All fields are required."
  - `password` must be at least 8 characters (matches the template's "Min. 8 characters" placeholder) — error: "Password must be at least 8 characters."
  - `email` must not already belong to an existing user (case-sensitive match against the `UNIQUE` column is sufficient at this stage) — error: "An account with this email already exists."
On success: hash the password, insert the new row, redirect to `/login` (PRG pattern — no form resubmission on refresh). Do not start a session or set any `session` keys — that is Step 3's responsibility.
There is no `confirm_password` field in the template — do not add one or validate against it
Do not implement login/logout/session handling in this step — scope is limited to account creation
Do not add email-format validation (e.g. regex) beyond the HTML5 `type="email"` field already in the template — keep server-side validation to the three checks above

Definition of done
- [ ] Visiting `/register` with `GET` still renders the form exactly as before (no regression)
- [ ] Submitting the form with any field empty is rejected with an inline error and no row is inserted
- [ ] Submitting a password under 8 characters is rejected with an inline error and no row is inserted
- [ ] Submitting a duplicate email is rejected with an inline error ("An account with this email already exists.") and no duplicate row is inserted
- [ ] Submitting valid, unique details creates a new row in `users` with a hashed (not plaintext) password and redirects to `/login`
- [ ] Refreshing the page after a successful submit does not re-submit the form (PRG pattern via redirect)
- [ ] The rejected-submission form re-populates `name` and `email` but never re-populates `password`
- [ ] No hex colour values appear in any touched code (no template changes expected, but the rule holds if any are touched)
