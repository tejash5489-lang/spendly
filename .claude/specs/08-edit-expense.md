Spec: Edit Expense

Overview
This feature implements the `/expenses/<id>/edit` route, replacing its Step 8 placeholder with a real form that lets a logged-in user update an existing expense's amount, category, date, and description. It reuses the same validation rules introduced in Step 7 (add expense), but adds an ownership check: a user may only edit expenses that belong to their own account, identified by `user_id` in the `expenses` table.

Depends on
Step 1: Database setup (`users`/`expenses` schema, `CATEGORIES` list) — implemented on `main`.
Step 3: Login and logout (`session['user_id']` established on login) — implemented on `main`.
Step 4/5: Profile page (renders transactions from `expenses`) — implemented on `main`; this step adds an "Edit" entry point into each transaction row.
Step 7: Add expense (`_validate_expense_form`, `add_expense.html` form patterns) — implemented on `main`; this step reuses the same validation function and form layout.

Routes
- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the expense's current values — logged-in only, and only if the expense belongs to the logged-in user
- `POST /expenses/<int:id>/edit` — validate and update the expense row, then redirect to `/profile` — logged-in only, and only if the expense belongs to the logged-in user

Both methods are handled by the existing `edit_expense` view (replace the Step 8 stub at app.py:282-284), guarded the same way as `profile()`: redirect to `/login` if `session.get("user_id")` is absent. If the expense doesn't exist, or exists but belongs to a different user, return a 404 rather than revealing that another user's expense exists.

Database changes
No schema changes. The existing `expenses` table already has every column this feature needs. Two query changes are required:
```sql
-- fetch the expense to edit, scoped to the logged-in user
SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?

-- apply the edit, scoped to the logged-in user (ownership enforced in SQL, not just app logic)
UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?
```
Additionally, `_get_recent_transactions` in `app.py` currently selects `date, description, category, amount` only — it must also select `id` so `profile.html` can link to `/expenses/<id>/edit` for each row.

Templates
Create: `templates/edit_expense.html` — extends `base.html`; same field layout as `add_expense.html` (amount, category, date, description), pre-populated with the expense's current values:
- Amount — `<input type="number" step="0.01" min="0.01">`, required, pre-filled
- Category — `<select>` populated from `CATEGORIES`, pre-selected to the current value
- Date — `<input type="date">`, required, pre-filled with the current value
- Description — `<input type="text">`, optional, pre-filled
- Submit button (`btn-submit`) — "Save Changes"
- Inline validation error messages rendered above the form on rejected submissions, re-populating the fields with the user's submitted values (same pattern as `add_expense.html`)
- "Back to profile" link (same pattern as `add_expense.html`)

Modify: `templates/profile.html` — in the "Recent Transactions" table, add an "Edit" link per row (e.g. a new `Actions` column) pointing to `{{ url_for('edit_expense', id=txn['id']) }}`.

Files to change
`app.py` — replace the `edit_expense` stub with a real view handling `GET` (render pre-filled form) and `POST` (validate, update, redirect); modify `_get_recent_transactions` to also select `id`.
`templates/profile.html` — add the "Edit" entry point to each transaction row.

Files to create
`templates/edit_expense.html`

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including amount/category/date/description/id
Passwords hashed with werkzeug (no auth changes in this step)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
Ownership guard: every `SELECT`/`UPDATE` against `expenses` for this route must filter on `user_id = ?` using the logged-in user's id — never trust the `<id>` from the URL alone
If no row matches `id` + `user_id`, return a 404 (do not distinguish "doesn't exist" from "belongs to someone else" in the response)
Reuse `_validate_expense_form` from Step 7 for server-side validation — do not duplicate its logic:
  - `amount` must parse as a positive number
  - `category` must be one of `CATEGORIES`
  - `date` must parse as `YYYY-MM-DD`
  - `description` is optional and may be empty
On validation failure, re-render `edit_expense.html` with an error message and the submitted values — do not raise a 500, and do not write a partial/invalid update
On success, redirect to `/profile` (PRG pattern — no form resubmission on refresh)
Do not implement delete (Step 9) in this step — scope is limited to editing existing expenses

Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense that belongs to another user returns a 404
- [ ] Visiting `/expenses/<id>/edit` for a non-existent id returns a 404
- [ ] Visiting `/expenses/<id>/edit` for your own expense shows a form pre-filled with its current amount, category, date, and description
- [ ] Submitting valid changes updates the row in `expenses` and redirects to `/profile`
- [ ] The updated values appear immediately in the profile page's transaction table, stats, and category breakdown
- [ ] Submitting a negative or zero amount is rejected with an inline error and the row is not updated
- [ ] Submitting a non-numeric amount is rejected with an inline error and the row is not updated
- [ ] Submitting an invalid/missing date is rejected with an inline error and the row is not updated
- [ ] Each row in the profile page's transaction table has a working "Edit" link to `/expenses/<id>/edit`
- [ ] Refreshing the page after a successful submit does not re-submit the form (PRG pattern via redirect)
- [ ] No hex colour values appear in the new template — only CSS variables
