Spec: Accounts and Balances

Overview
This feature lets a user track running balances across multiple money sources — Cash, a Wallet (e.g. Paytm/PhonePe), and any number of named Bank accounts (e.g. "HDFC Bank", "SBI Savings") — separately from each other. Each account has its own balance, set when the account is created and adjustable later via a manual "add funds" top-up. Expenses can optionally be linked to one of these accounts; doing so decrements that account's balance by the expense amount, and edits/deletes to a linked expense keep the linked account's balance in sync. This is independent from the existing `payment_method` tag (Cash/Card/UPI, added in Step 10) — that stays a simple classification field; accounts are a separate, optional balance-tracking layer on top. An account's balance is allowed to go negative (e.g. overdraft) — there is no blocking on insufficient funds.

Depends on
Step 01 — Database Setup (`users` table, `get_db()`, `init_db()`)
Step 07 — Add Expense (`/expenses/add`, `_validate_expense_form`)
Step 08 — Edit Expense (`/expenses/<id>/edit`)
Step 09 — Delete Expense (`/expenses/<id>/delete`)

Note: independent of Step 10 (Payment Method) — that step lives on its own branch and is not a prerequisite here; this spec does not touch `payment_method`.

Routes
- `GET /accounts` — list the logged-in user's accounts with their balances, plus the "add account" form — logged-in only
- `POST /accounts/add` — create a new account (name, type, starting balance) for the logged-in user, redirect to `/accounts` — logged-in only
- `POST /accounts/<int:id>/add-funds` — add a positive amount to an existing account's balance (must belong to the logged-in user), redirect to `/accounts` — logged-in only

`GET/POST /expenses/add` and `GET/POST /expenses/<id>/edit` are extended (not new routes) to accept an optional `account_id` field. `POST /expenses/<id>/delete` (Step 09) is extended to reverse the balance effect of the expense being deleted.

Database changes
New table:
```sql
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```
`type` is free text, not a fixed enum — a user should be able to label an account "Wallet", "Home Cash", "HDFC Bank", or anything else without being constrained to a preset list (this differs from `CATEGORIES`/`PAYMENT_METHODS`, which are closed sets). `ACCOUNT_TYPES = ["Cash", "Wallet", "Bank"]` exists only as autocomplete suggestions (an HTML `<datalist>`), not a validation constraint. `name` is likewise free text (e.g. "HDFC Bank", "Everyday Wallet") so a user can have several accounts of the same `type` (multiple banks).

Add a nullable FK column to `expenses`:
```sql
account_id INTEGER REFERENCES accounts (id)
```
Nullable because linking an expense to an account is optional — an expense with no account behaves exactly as it does today (no balance effect).

As with Step 10's `payment_method` migration, `init_db()` must handle pre-existing databases: `CREATE TABLE IF NOT EXISTS accounts` only helps fresh DBs, and adding `account_id` to an already-existing `expenses` table requires the same `PRAGMA table_info(expenses)` guard-and-`ALTER TABLE ADD COLUMN` pattern already used for `payment_method`.

`seed_db()` should create 2-3 demo accounts for the seeded user (e.g. "Cash" / Cash / ₹2000 starting balance, "Wallet" / Wallet / ₹500, "HDFC Bank" / Bank / ₹15000) and link a couple of the existing sample expenses to them (adjusting those accounts' seeded balances down to stay consistent, since a linked expense's amount should already be reflected in the account's starting balance).

Templates
Create: `templates/accounts.html` — lists each account (name, type, balance) and has two forms: "Add account" (name, free-text type field with `<datalist>` suggestions from `ACCOUNT_TYPES`, starting balance) and, per account row, a small "Add funds" form (amount input only, posts to `/accounts/<id>/add-funds`).

Modify:
- `templates/add_expense.html` — add an optional "Account" `<select>` (options: "None" + the user's accounts by name) after the existing Payment method field.
- `templates/edit_expense.html` — same field, pre-selected to the expense's current `account_id` (or "None").
- `templates/base.html` — add an "Accounts" nav link next to "Profile"/"Analytics" in the logged-in nav block.

Files to change
- `database/db.py` — add `ACCOUNT_TYPES` constant; add the `accounts` `CREATE TABLE IF NOT EXISTS`; add `account_id` to the `expenses` `CREATE TABLE IF NOT EXISTS`; add the `PRAGMA table_info` migration guard for `account_id` on existing DBs; update `seed_db()` to create demo accounts and link some sample expenses to them.
- `app.py`:
  - Import `ACCOUNT_TYPES`.
  - New `accounts()` view (`GET`/`POST /accounts`): `GET` fetches and renders the user's accounts; `POST` validates `name` (non-empty), `type` (non-empty free text — no membership check), `balance` (must parse as a finite number; negative allowed, consistent with balances being allowed to go negative), inserts a new row, redirects to `/accounts`.
  - New `add_funds(id)` view (`POST /accounts/<id>/add-funds`): loads the account, 404s if it doesn't belong to the logged-in user, validates `amount` is a finite positive number, does `UPDATE accounts SET balance = balance + ? WHERE id = ?`, redirects to `/accounts`.
  - `add_expense()`: read optional `account_id` from the form; if present, validate it parses as an int and belongs to the logged-in user (else error "Invalid account selected."); on successful insert, if an account was selected, also `UPDATE accounts SET balance = balance - ? WHERE id = ?` with the expense amount, in the same connection/transaction as the insert.
  - `edit_expense(id)`: fetch the expense's current `account_id` alongside its other fields; on successful update, reconcile balances — if the expense previously had an account, add the old amount back to it; if the (possibly different) new account_id is set, subtract the new amount from it. Both adjustments happen in the same transaction as the `UPDATE expenses`.
  - `delete_expense(id)`: before deleting, check the expense's `account_id`; if set, add the expense's amount back to that account's balance in the same transaction as the delete.
- `templates/add_expense.html`, `templates/edit_expense.html`, `templates/base.html` — see Templates section.

Files to create
- `templates/accounts.html`

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL values
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
`type` validation for accounts mirrors the existing `CATEGORIES`/`PAYMENT_METHODS` pattern — membership check, generic error message
Account balance updates always happen in the same connection as the triggering expense insert/update/delete, committed together — never as a separate uncommitted step that could leave balance and expense rows inconsistent if the process dies mid-request
Ownership checks on every account mutation — `add_funds`, and any `account_id` referenced from an expense form, must belong to `session["user_id"]`; never trust a client-supplied account id without checking
Balances are allowed to go negative — do not add insufficient-funds validation or blocking
Do not add account editing/renaming or account deletion — out of scope for this step (creation + top-up only)
Do not change or reference `payment_method` — this step is independent of Step 10

Definition of done
- [ ] `accounts` table exists; a pre-existing `spendly.db` (from before this change) gains the table and the `expenses.account_id` column without erroring
- [ ] `GET /accounts` (logged in) lists the user's accounts with correct balances and an "Add account" form
- [ ] Submitting "Add account" with name="Emergency Fund", type="Bank", balance="1000" creates the account and shows it in the list
- [ ] Submitting "Add funds" on an account increases its balance by the submitted amount and does not affect other accounts
- [ ] `GET /expenses/add` shows an Account dropdown with "None" plus the user's accounts
- [ ] Adding an expense with an account selected decrements that account's balance by the expense amount; leaving it as "None" leaves all balances unchanged
- [ ] Editing an expense to change its amount (same account) adjusts that account's balance by the difference
- [ ] Editing an expense to switch from one account to another correctly reverses the balance effect on the old account and applies it to the new one
- [ ] Deleting an expense that was linked to an account adds its amount back to that account's balance
- [ ] An account's balance can go negative (e.g. add an expense larger than the balance) without being blocked or erroring
- [ ] A user cannot add funds to, or link an expense to, another user's account (ownership-checked, 404 or generic error on mismatch)
- [ ] The nav bar shows an "Accounts" link when logged in
- [ ] No hex colour values appear in any touched template
