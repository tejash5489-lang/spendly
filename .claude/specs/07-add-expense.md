Spec: Add Expense

Overview
This feature implements the `/expenses/add` route, replacing its Step 7 placeholder with a real form that lets a logged-in user record a new expense — amount, category, date, and an optional description. It's the first write path in the app: every prior step (registration, login, profile) only reads or authenticates; this step inserts a new row into the `expenses` table tied to the logged-in user, which is what the profile page's stats, transaction history, and category breakdown have been rendering all along.

Depends on
Step 1: Database setup (`users`/`expenses` schema, `CATEGORIES` list) — implemented on `main`.
Step 3: Login and logout (`session['user_id']` established on login) — implemented on `main`.
Step 4/5: Profile page (renders transactions/stats from `expenses`) — implemented on `main`; this step is what the profile page redirects to via the "Add Expense" action.

Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense row, then redirect to `/profile` — logged-in only

Both methods are handled by the existing `add_expense` view (replace the Step 7 stub at app.py:220-222), guarded the same way as `profile()`: redirect to `/login` if `session.get("user_id")` is absent.

Database changes
No schema changes. The existing `expenses` table (`database/db.py`) already has every column this feature needs: `user_id`, `amount`, `category`, `date`, `description`. Insert via:
```sql
INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)
```

Templates
Create: `templates/add_expense.html` — extends `base.html`; a form with:
- Amount — `<input type="number" step="0.01" min="0.01">`, required
- Category — `<select>` populated from `CATEGORIES` (passed from the view, same list `profile.html` already uses)
- Date — `<input type="date">`, required, defaulting to today's date
- Description — `<input type="text">`, optional
- Submit button (`btn-primary`) — "Add Expense"
- Inline validation error messages (e.g. "Amount must be greater than 0") rendered above the form when the server rejects a submission, re-populating the fields with the user's previously submitted values so nothing is lost on error

Modify: `templates/profile.html` — add an "Add Expense" link/button (`btn-primary`, `href="{{ url_for('add_expense') }}"`) near the profile header or stats row, giving users an entry point into the form.

Files to change
`app.py` — replace the `add_expense` stub with a real view handling `GET` (render form) and `POST` (validate, insert, redirect).
`templates/profile.html` — add the "Add Expense" entry point.

Files to create
`templates/add_expense.html`

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including amount/category/date/description
Passwords hashed with werkzeug (no auth changes in this step)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
Server-side validation is mandatory even though HTML5 input constraints (`required`, `min`, `type="date"`) provide a first line of defense — never trust client-side validation alone:
  - `amount` must parse as a positive number
  - `category` must be one of `CATEGORIES`
  - `date` must parse as `YYYY-MM-DD`
  - `description` is optional and may be empty
On validation failure, re-render `add_expense.html` with an error message and the submitted values — do not raise a 500, and do not insert a partial/invalid row
On success, redirect to `/profile` (PRG pattern — no form resubmission on refresh)
The inserted row's `user_id` always comes from `session['user_id']`, never from client input — a user must never be able to create an expense for another user's account
Do not implement edit or delete (Steps 8/9) in this step — scope is limited to creating new expenses

Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount, category (from `CATEGORIES`), date (defaulted to today), and description fields
- [ ] Submitting valid data creates a new row in `expenses` with the correct `user_id`, and redirects to `/profile`
- [ ] The newly added expense appears immediately in the profile page's transaction table, stats, and category breakdown
- [ ] Submitting a negative or zero amount is rejected with an inline error and no row is inserted
- [ ] Submitting a non-numeric amount is rejected with an inline error and no row is inserted
- [ ] Submitting an invalid/missing date is rejected with an inline error and no row is inserted
- [ ] Submitting with description left blank succeeds (description is optional)
- [ ] Refreshing the page after a successful submit does not re-submit the form (PRG pattern via redirect)
- [ ] No hex colour values appear in the new template — only CSS variables
