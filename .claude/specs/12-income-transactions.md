Spec: Income Transactions

Overview
This feature lets a user record money coming in — salary, money received from someone, refunds, interest, or other income — as its own kind of transaction, kept separate from expenses (a distinct "Income" flow, not merged into the expense table/list, mirroring how Accounts (Step 11) is its own separate concept from Expenses). Every income entry must be linked to an account (Cash/Wallet/Bank, from Step 11) — unlike expenses, where linking is optional — because receiving money always means it lands somewhere specific. Adding income increases the linked account's balance; editing or deleting an income entry keeps that balance reconciled, mirroring the reconciliation logic already used for expenses but with the sign flipped (income adds, expenses subtract).

Depends on
Step 01 — Database Setup (`users` table, `get_db()`, `init_db()`)
Step 11 — Accounts and Balances (`accounts` table, `_get_accounts`, account balance reconciliation pattern) — not yet on `main`, so this feature branch is cut from `feature/accounts-balance` instead of `main`.

Routes
- `GET /income/add` — render the add-income form — logged-in only
- `POST /income/add` — validate and insert a new income row, credit the linked account's balance, redirect to `/profile` — logged-in only
- `GET /income/<int:id>/edit` — render the edit-income form, pre-filled — logged-in only
- `POST /income/<int:id>/edit` — validate and update the income row, reconcile the (possibly changed) account's balance, redirect to `/profile` — logged-in only
- `POST /income/<int:id>/delete` — delete the income row, reverse its balance effect on the linked account, redirect to `/profile` — logged-in only

Database changes
New table:
```sql
CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```
`category` is validated at the app layer against a new `INCOME_CATEGORIES = ["Salary", "Gift", "Refund", "Interest", "Other"]` constant (same closed-list pattern as `CATEGORIES`, not free text like `ACCOUNT_TYPES`). `account_id` is `NOT NULL` — every income row must be linked to an account (per this spec's scope decision). No migration guard is needed for pre-existing DBs beyond the standard `CREATE TABLE IF NOT EXISTS`, since this is a brand new table, not a new column on an existing table.

`seed_db()` should add 1-2 sample income rows for the demo user (e.g. a "Salary" credit to the HDFC Bank account), with the linked account's seeded `balance` in `seed_db()` adjusted upward to already include it (same "precompute the post-effect balance" approach used for the linked sample expenses).

Templates
Create:
- `templates/add_income.html` — mirrors `templates/add_expense.html`'s structure (`.auth-section` / `.auth-container` / `.auth-card`) with fields: Amount, Category (`<select>` from `INCOME_CATEGORIES`, required), Account (`<select>` from the user's accounts, required — no "None" option, unlike the expense form's optional account field), Date (defaults to today), Description (optional).
- `templates/edit_income.html` — same fields, pre-filled from the existing row.

Modify:
- `templates/profile.html` — add a second "Recent Income" table below the existing "Recent Transactions" table, same `.profile-table` styling, columns: Date, Description, Category, Account, Amount, Actions (Edit/Delete links matching the expense table's action-cell pattern). Add an "Add Income" button in the `.profile-header` next to the existing "Add Expense" button.

Files to change
- `database/db.py` — add `INCOME_CATEGORIES` constant; add the `income` `CREATE TABLE IF NOT EXISTS` (after `accounts`, since it references it); update `seed_db()` to insert 1-2 sample income rows and adjust the relevant seeded account balance upward to match.
- `app.py`:
  - Import `INCOME_CATEGORIES`.
  - Add `_validate_income_form(form_values)`, mirroring `_validate_expense_form`: amount must be finite and positive, `category` must be in `INCOME_CATEGORIES`, date must parse. Returns `(amount, error)`.
  - Reuse `_resolve_account_id` for the account field, but since it's required here (unlike the optional expense field), treat an empty/blank value as an error ("Please select an account.") before calling it — don't fall through to the "no account" `None` case that expenses use.
  - New `add_income()` view (`GET`/`POST /income/add`): mirrors `add_expense()`'s structure, but on success the `INSERT INTO income (...)` is paired with `UPDATE accounts SET balance = balance + ? WHERE id = ? AND user_id = ?` (credit, not debit) — same connection, one `commit()`.
  - New `edit_income(id)` view (`GET`/`POST /income/<id>/edit`): mirrors `edit_expense()`'s reconciliation — but with signs flipped: always reverse the *old* amount from the *old* account (`balance -= old_amount`) and apply the *new* amount to the *new* account (`balance += new_amount`), both unconditional-on-each-other exactly as `edit_expense` does (collapses correctly for same-account edits into a net delta, and for account-switch edits into a full reversal + full re-application).
  - New `delete_income(id)` view (`POST /income/<id>/delete`): mirrors `delete_expense()` — delete the row, then `UPDATE accounts SET balance = balance - ? ...` (reverse the credit) in the same transaction.
  - `profile()`: fetch recent income rows (new `_get_recent_income(conn, user_id, start, end, limit=10)` helper, following the same `_where_clause` + date-filter pattern as `_get_recent_transactions`, joined or not against `accounts` to also select the account's `name` for display) and pass to `profile.html`.
- `templates/profile.html`, `templates/add_income.html`, `templates/edit_income.html` — see Templates section.

Files to create
- `templates/add_income.html`
- `templates/edit_income.html`

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL values
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
`category` validation for income mirrors the existing `CATEGORIES` pattern exactly — membership check, generic error message
Account balance updates always happen in the same connection as the triggering income insert/update/delete, committed together — never as a separate uncommitted step
Ownership checks on every account reference — an income entry's `account_id` must belong to `session["user_id"]`, reusing `_resolve_account_id`'s existing ownership-check logic
`account_id` is required for income (unlike the optional field on expenses) — reject a blank submission with a clear error before any DB write
Do not add income editing of `payment_method` — income has no payment method concept, only expenses do
Do not merge income and expenses into a single combined list/table in this step — keep them visually and structurally separate, per this spec's scope

Definition of done
- [ ] `income` table exists after `init_db()` runs
- [ ] `GET /income/add` (logged in) shows a form with Amount, Category (Salary/Gift/Refund/Interest/Other), Account (required, no "None" option), Date (defaults today), Description (optional)
- [ ] Submitting valid income data inserts a row, credits the selected account's balance by the amount, and redirects to `/profile`
- [ ] Submitting without selecting an account shows "Please select an account." and does not insert a row or touch any balance
- [ ] Submitting with an invalid/unowned account id is rejected the same way (no silent success, no cross-user balance mutation)
- [ ] The profile page shows a "Recent Income" table separate from "Recent Transactions" (expenses), with a working "Add Income" button in the header
- [ ] Editing an income entry's amount (same account) shifts that account's balance by the delta
- [ ] Editing an income entry to switch accounts correctly reverses the credit on the old account and applies it to the new one
- [ ] Deleting an income entry reverses its credit on the linked account
- [ ] The `/accounts` page balances reflect income credits correctly alongside expense debits
- [ ] No hex colour values appear in any touched template
