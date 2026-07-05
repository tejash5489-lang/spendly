# Spec: Profile Page Design

## Overview

This feature implements the real `/profile` page for Spendly, replacing the
current placeholder (`"Profile page — coming in Step 4"`). It gives a
logged-in user a dedicated page showing their own account details — name,
email, and member-since date — read from the `users` row created in Step 2
(Registration) and identified via the session set up in Step 3 (Login and
Logout). This is a read-only account page; it does not add editing, expense
stats, or CRUD (those are separate, later steps). It's a natural companion to
the existing `/welcome` page (a one-line post-login landing message) but is a
distinct, permanent, linked-from-nav destination rather than a login redirect
target.

## Depends on

- Step 1 (Database setup) — `database/db.py` with `get_db()` and the `users`
  table.
- Step 2 (Registration) — `users` rows with `name`/`email`/`created_at`.
- Step 3 (Login and Logout) — `session["user_id"]` set on login, which
  `/profile` uses to look up the current user and to guard the page.

## Routes

- `GET /profile` — shows the logged-in user's name, email, and member-since
  date; redirects to `/login` if no session exists — logged-in

## Database changes

No database changes. The existing `users` table (`id`, `name`, `email`,
`password_hash`, `created_at`) already has everything this page displays.

## Templates

**Create:**
- `templates/profile.html` — extends `base.html`; shows the user's name,
  email, and formatted member-since date in a card, reusing the existing
  `.auth-card`/`.legal-section` visual patterns (no new component system).

**Modify:**
- `templates/base.html` — when `session.get('user_id')` is set, add a
  "Profile" link (to `{{ url_for('profile') }}`) alongside the existing
  "Logout" link in `.nav-links`, so the page is actually reachable from the
  UI. No change to the logged-out nav state.

## Files to change

- `app.py` — implement `/profile`: if `"user_id" not in session`, redirect to
  `url_for("login")`; otherwise `get_db()`, `SELECT name, email, created_at
  FROM users WHERE id = ?` with the session's `user_id`, close the
  connection, and render `profile.html` with that row.
- `templates/base.html` — add the "Profile" nav link as described above.

## Files to create

- `templates/profile.html` as described above.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Read-only: no form, no edit/update endpoint, no password change — that's
  out of scope for this step
- Do not touch `/welcome`, the login/logout redirect targets, or the
  `/expenses/*` stubs — this step only adds `/profile` and its nav link

## Definition of done

- [ ] Visiting `/profile` while logged in shows the current session user's
      name, email, and a member-since date (not some other user's data)
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] The nav shows a "Profile" link alongside "Logout" when logged in
- [ ] The nav shows neither link when logged out (unchanged "Sign in" / "Get
      started")
- [ ] `/welcome`, `/login`, `/logout`, `/register` behavior is unchanged
- [ ] Existing routes (`/`, `/terms`, `/privacy`) are unaffected
