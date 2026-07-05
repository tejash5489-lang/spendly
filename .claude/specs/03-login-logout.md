# Spec: Login and Logout

## Overview

This feature implements real session-based authentication for Spendly. The
`/login` route currently only renders `login.html` on GET — the form it
already posts to `/login` has no handler, which is why submitting it
currently fails with "Method Not Allowed". `/logout` is a stub that returns
placeholder text. This step adds the server-side logic to verify a user's
email/password against the `users` table created in Step 1 and populated by
Step 2 (Registration), start a logged-in session on success, and let the user
end that session via logout. This is the first step that reads authentication
state, and it is a prerequisite for Step 4 (Profile), which will need to know
who the current user is.

## Depends on

- Step 1 (Database setup) — `database/db.py` with `get_db()` and the `users`
  table.
- Step 2 (Registration) — `users` rows with `password_hash` values created by
  `POST /register`, so there is something to log in against.

## Routes

- `GET /login` — renders the login form (already implemented, unchanged) —
  public
- `POST /login` — validate submitted `email`/`password` against `users`; on
  success start a session and redirect to `/`; on failure (missing fields,
  unknown email, or wrong password) re-render `login.html` with a single
  generic error — public
- `GET /logout` — clear the session and redirect to `/` — logged-in (safe to
  hit while logged out too; it will simply no-op and redirect)

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`,
`password_hash`, `created_at`) already supports login as-is.

## Templates

**Create:** none

**Modify:**
- `templates/base.html` — the nav currently always shows "Sign in" / "Get
  started". Change it to check `session.get("user_id")`: when logged in, show
  a "Logout" link (`{{ url_for('logout') }}`) instead; when logged out, show
  the existing "Sign in" / "Get started" links unchanged. This is the only way
  a logged-in user can discover how to log out, since `/profile` (Step 4)
  doesn't exist yet.
- `templates/login.html` — no structural change; it already posts to `/login`
  and already renders `{{ error }}` when present.

## Files to change

- `app.py`:
  - Set `app.secret_key` (required for Flask sessions) to a hardcoded dev
    value — this is a learning project with no env-based config yet; a real
    secret/env var is a concern for a future deployment step, not this one.
  - Add `methods=["GET", "POST"]` to `/login` and implement the POST branch:
    read `email`/`password` from `request.form`, validate both are present,
    look up the user by email via `get_db()`, verify the password with
    `check_password_hash`, and on success set `session["user_id"]` and
    `session["user_name"]` then redirect to `/`. On any failure, re-render
    `login.html` with `error="Invalid email or password."` — use one generic
    message for "no such email" and "wrong password" so login can't be used
    to enumerate registered emails.
  - Implement `/logout`: `session.clear()` then redirect to `/`.
- `templates/base.html` — conditional nav as described above.

## Files to create

No new files.

## New dependencies

No new dependencies. `check_password_hash` is already part of
`werkzeug.security` (same package `generate_password_hash` comes from).

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords verified with werkzeug's `check_password_hash` — never compare
  plaintext or roll a custom comparison
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do not implement `/profile` or any route-protection/`login_required`
  machinery — that's Step 4; this step only establishes and clears the
  session
- Use one generic error message for all login failures (don't reveal whether
  the email exists)

## Definition of done

- [ ] Submitting `/login` with a registered email and correct password
      redirects to `/` and the nav now shows "Logout" instead of "Sign in" /
      "Get started"
- [ ] Submitting `/login` with a registered email and wrong password
      re-renders `login.html` with "Invalid email or password." and no
      session is created
- [ ] Submitting `/login` with an email that doesn't exist re-renders
      `login.html` with the same "Invalid email or password." message
- [ ] Submitting `/login` with a missing email or password re-renders
      `login.html` with an error and no DB query is attempted
- [ ] Visiting `/logout` after logging in clears the session and redirects to
      `/`, and the nav reverts to showing "Sign in" / "Get started"
- [ ] Visiting `/logout` while already logged out doesn't error — it just
      redirects to `/`
- [ ] `GET /login` still renders the empty form as before
- [ ] Existing routes (`/`, `/register`, `/terms`, `/privacy`) are unaffected
