Spec: Payment Method for Expenses

Overview
This feature tags every expense with how it was paid for — Cash, Card, or UPI. It extends the existing add-expense and edit-expense flows (Steps 07 and 08) with a required "Payment method" field, stored alongside the existing `category` column on the `expenses` table, and displayed in the transaction table on the profile page. This is a simple classification tag only — it does not track running balances per method (no wallet/account balance ledger; that is explicitly out of scope for this step).

Depends on
Step 01 — Database Setup (`expenses` table, `get_db()`, `init_db()`)
Step 07 — Add Expense (`/expenses/add`, `_validate_expense_form`)
Step 08 — Edit Expense (`/expenses/<id>/edit`)

Routes
No new routes. `GET/POST /expenses/add` and `GET/POST /expenses/<id>/edit` are extended to also handle the `payment_method` field.

Database changes
Add a `payment_method` column to the existing `expenses` table:
```sql
payment_method TEXT NOT NULL DEFAULT 'Cash'
```
No `CHECK` constraint — valid values are enforced at the application layer via a `PAYMENT_METHODS` list, matching the existing pattern used for `CATEGORIES` (which also has no DB-level constraint).

Because `init_db()` uses `CREATE TABLE IF NOT EXISTS`, it will not add this column to an already-existing `spendly.db` on a developer's machine. `init_db()` must therefore run a small migration after the `CREATE TABLE` statements: check `PRAGMA table_info(expenses)` for a `payment_method` column, and if it's missing, run `ALTER TABLE expenses ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Cash'`. This keeps existing rows and the fresh-DB path both working.

`seed_db()`'s sample expenses should each specify a `payment_method` (mix of `Cash`, `Card`, `UPI`) instead of relying on the column default, so seeded data exercises all three values.

Templates
Create: none.

Modify:
- `templates/add_expense.html` — add a "Payment method" `<select>` field (Cash / Card / UPI) directly after the Category field, following the same markup pattern as the category `<select>`.
- `templates/edit_expense.html` — same field, pre-selected to the expense's current `payment_method`.
- `templates/profile.html` — add a "Payment" column to the transaction table (between Category and Amount), rendering `txn['payment_method']` as plain text (no new badge styling needed — reuse existing table cell styling).

Files to change
- `database/db.py` — add `PAYMENT_METHODS = ["Cash", "Card", "UPI"]` constant; add `payment_method` column to the `CREATE TABLE` statement for `expenses`; add the `PRAGMA table_info` migration step in `init_db()`; update `seed_db()`'s sample expense tuples to include a `payment_method` value each.
- `app.py` — import `PAYMENT_METHODS` from `database.db`; update `_validate_expense_form` to validate `payment_method` is one of `PAYMENT_METHODS`; update `add_expense()` and `edit_expense()` to read `payment_method` from the form, include it in `form_values`, pass `payment_methods=PAYMENT_METHODS` to both templates, and include it in the `INSERT`/`UPDATE` statements; update the `SELECT` in `edit_expense()` to also fetch `payment_method`; update `_get_recent_transactions()`'s `SELECT` to also fetch `payment_method` so it's available to `profile.html`.
- `templates/add_expense.html`, `templates/edit_expense.html`, `templates/profile.html` — see Templates section above.

Files to create
None.

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL values (the `payment_method` migration's `ALTER TABLE` statement has no user input, so it's the one exception that's a static string)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
`payment_method` validation follows the exact same shape as the existing `category` validation in `_validate_expense_form` — membership check against `PAYMENT_METHODS`, generic error message ("Please select a valid payment method.") on failure
Do not add per-method balance tracking, top-ups, or a wallet/account ledger — this step is a tag only
Do not add new payment methods beyond Cash, Card, UPI unless asked

Definition of done
- [ ] `expenses` table has a `payment_method` column; running the app against a pre-existing `spendly.db` (created before this change) does not error — the migration adds the column automatically
- [ ] `GET /expenses/add` shows a Payment method dropdown with Cash/Card/UPI, no option pre-selected
- [ ] Submitting `/expenses/add` without selecting a payment method shows "Please select a valid payment method." and does not insert a row
- [ ] Submitting `/expenses/add` with a valid payment method inserts the expense with that value and redirects to `/profile`
- [ ] `GET /expenses/<id>/edit` pre-selects the expense's current payment method in the dropdown
- [ ] Submitting `/expenses/<id>/edit` with a different payment method updates the row
- [ ] The profile page's transaction table shows a Payment column with the correct value for each row
- [ ] Seeded demo data (`seed_db()`) contains expenses with at least two different payment methods
- [ ] No hex colour values appear in any touched template
