# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is **Spendly**, a Flask expense-tracker app built incrementally as a step-by-step learning exercise, driven by numbered spec files in `.claude/specs/` (`01-database-setup.md` … `12-income-transactions.md`). Each spec documents one feature step's routes, schema changes, and a testable Definition of Done; a matching `tests/test_NN-<slug>.py` is written *from the spec*, not from the implementation (black-box). Custom slash commands encode the workflow: `/create-spec` (write the next numbered spec + cut its branch), `/test-feature` (write + run tests for a spec), `/code-review-feature` (parallel quality + security subagent review), `/ship-feature` (commit, push, PR, squash-merge, branch cleanup). When asked to "implement the next step," check `.claude/specs/` for the next unwritten step number and existing routes/templates for what's still a placeholder — don't jump ahead.

Current state: registration, login/logout (session-based, `session["user_id"]`/`session["user_name"]`), the profile page (with date-range filtering, income/expense stats, account balances), full expense CRUD (with payment method + optional linked account), full income CRUD (with a required linked account), and accounts with running balances (create, top-up, inline creation from the expense/income forms) are all implemented. `/analytics` is still a "Coming Soon" placeholder page — that's the only remaining unbuilt piece.

## Commands

Run these from the project root (where `app.py` lives).

```bash
# activate the venv (Windows)
venv\Scripts\activate

# install deps
pip install -r requirements.txt

# run the dev server (http://localhost:5001)
python app.py

# run the full test suite
pytest

# run one spec's tests, or a single test
pytest tests/test_07-add-expense.py
pytest tests/test_07-add-expense.py::test_post_valid_expense_inserts_row_and_redirects_to_profile
```

There is no lint/format tooling configured in this repo yet.

## Architecture

- **`app.py`** — single-file Flask app; all routes and helpers are defined directly on `app` (no blueprints). `debug=True`, runs on port `5001`. `init_db()`/`seed_db()` run once at import time inside `with app.app_context()`. Recurring patterns to follow when adding routes:
  - Every logged-in route starts with `if "user_id" not in session: return redirect(url_for("login"))`.
  - Form handling is GET-renders-form / POST-validates-then-inserts-then-redirects (PRG). Validation lives in dedicated `_validate_*_form(form_values)` helpers returning `(value, error)`; on error the same template is re-rendered with `error` and the submitted `form_values` (passwords are the one exception — never re-populated).
  - `_resolve_account_id(conn, user_id, raw, new_name="", new_type="")` is the single place that turns a submitted `account_id` into a real, ownership-checked account id — including the `"__new__"` sentinel value the expense/income forms use for their inline "+ Add a new account" option (which creates the account on the fly instead of resolving an existing one).
  - `_where_clause(user_id, start, end, prefix="")` builds the shared `user_id = ? [AND date >= ?] [AND date <= ?]` filter; pass a table prefix (e.g. `"income."`) when the query joins another table that also has a `user_id`/`date` column, to avoid ambiguous-column errors.
  - **Account balance reconciliation is a hard invariant**: any insert/edit/delete of an expense or income row that touches `account_id` must update the linked account's `balance` in the *same* connection/transaction as the row change, committed together. Expenses debit, income credits; edits reverse the old effect and apply the new one (even across an account switch). Balances are allowed to go negative — no insufficient-funds blocking anywhere.
- **`database/db.py`** — the sole database access point: `get_db()` (SQLite connection, `row_factory`, foreign keys on), `init_db()` (schema via `CREATE TABLE IF NOT EXISTS`, plus `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` migration guards for columns added to `expenses` after it originally shipped — follow this guard pattern for any new column on an existing table), `seed_db()` (no-ops if any user already exists; seeds one demo user with accounts/expenses/income whose balances are pre-computed to already reflect the linked sample rows). Closed-vocabulary constants (`CATEGORIES`, `PAYMENT_METHODS`, `INCOME_CATEGORIES`) are validated at the app layer with a plain membership check; `ACCOUNT_TYPES` is free text — the constant only feeds an HTML `<datalist>` suggestion list, not a validation rule.
- **`templates/`** — Jinja2, all extending `templates/base.html` (`{% block title %}` / `{% block content %}` / `{% block scripts %}`). The nav in `base.html` branches on `session.get('user_id')`. Static assets go through `url_for('static', filename=...)`.
- **`static/css/style.css`** — shared site styling (CSS variables for all colors, no hardcoded hex); `static/css/landing.css` — landing-page-only styling.
- **`static/js/main.js`** — plain script tag from `base.html`, no build step/bundler; currently just the show/hide toggle for the inline "new account" fields on the expense/income forms.
- **`tests/conftest.py`** — `app_module` reloads `app.py` against a temp SQLite file (patches `database.db.DB_PATH` before import so `init_db()`/`seed_db()` run against the temp DB); `client` wraps it in a Flask test client; `logged_in_client` pre-seeds the session as the demo user (`id=1`). Use `logged_in_client` for anything behind the login gate.
- Branding: product name is "Spendly", tagline "Track every rupee. Own your finances." (currency/audience context is INR — render amounts as `₹`, never `$`).
