# Spec: Registration

## Overview

This feature implements real account creation for Spendly. The `/register` route
currently only renders `register.html` on GET; there is no handling for the POST
submission the form already sends. This step adds the server-side logic to validate
the submitted name/email/password, hash the password, persist a new row in the
`users` table, and give the user feedback on success or failure. This is the first
step that writes to the database via user input, and it lays the groundwork
(a real `users` row) that the future login/logout and profile steps depend on.

## Depends on

- Step 1 (Database setup) — `database/db.py` with `get_db()`, `init_db()`, and the
  `users` table schema must already exist. It does.

## Routes

- `GET /register` — renders the registration form (already implemented, unchanged)
- `POST /register` — validate submitted `name`, `email`, `password`; if invalid or
  the email is already registered, re-render `register.html` with an `error`
  message; otherwise hash the password, insert the new user, and redirect to
  `/login` — public

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`,
`password_hash`, `created_at`) already supports registration as-is.

## Templates

**Create:** none

**Modify:**
- `templates/register.html` — no structural change; it already posts to
  `/register` and already renders `{{ error }}` when present, so it only needs
  the backend behind it

## Files to change

- `app.py` — add `methods=["GET", "POST"]` to the `/register` route and implement
  the POST branch: read form fields, validate, check for an existing email via
  `get_db()`, hash the password with `generate_password_hash`, insert the row,
  commit, close the connection, and redirect to `/login` on success (re-render
  `register.html` with `error` set on failure)

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do not implement session/login logic (setting a logged-in session) — that
  belongs to the future login/logout step; registration only creates the account
  and redirects to `/login`
- Validate on the server even though the form has `required`/`type="email"`
  attributes (client-side HTML validation is not a substitute for server checks)

## Definition of done

- [ ] Submitting the register form with a new name/email/password creates a row
      in the `users` table with a hashed (not plaintext) password
- [ ] After a successful registration, the browser is redirected to `/login`
- [ ] Submitting the register form with an email that already exists in `users`
      re-renders `register.html` with a visible error message and does not
      create a duplicate row
- [ ] Submitting with a missing name, email, or password re-renders
      `register.html` with a visible error message and does not touch the
      database
- [ ] `GET /register` still renders the empty form as before
- [ ] Existing routes (`/`, `/login`, `/terms`, `/privacy`) are unaffected
