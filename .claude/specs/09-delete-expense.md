Spec: Delete Expense

Overview
This feature implements the `/expenses/<id>/delete` route, replacing its Step 9 placeholder with real logic that permanently removes an expense row belonging to the logged-in user. It completes the CRUD set for expenses (Step 7 add, Step 8 edit, Step 9 delete), giving users a way to remove mistaken or duplicate entries from their profile page.

Depends on
Step 1: Database setup (`users`/`expenses` schema) — implemented on `main`.
Step 3: Login and logout (`session['user_id']` established on login) — implemented on `main`.
Step 4/5: Profile page (renders transactions from `expenses`, now including `id`) — implemented on `main`.
Step 8: Edit expense (ownership-guard pattern reused here: `SELECT ... WHERE id = ? AND user_id = ?`) — implemented on `main`.

Routes
- `POST /expenses/<int:id>/delete` — delete the expense row, then redirect to `/profile` — logged-in only, and only if the expense belongs to the logged-in user

The existing stub is a bare `GET` route (`app.py:340-342`); it must be replaced with a `POST`-only route. Deleting via `GET` is unsafe (crawlers/prefetchers can trigger it), so the profile page's "Delete" action becomes a small `<form method="POST">` rather than a plain link.

Guarded the same way as `edit_expense`: redirect to `/login` if `session.get("user_id")` is absent. If the expense doesn't exist, or exists but belongs to a different user, return a 404 rather than revealing that another user's expense exists.

Database changes
No schema changes. One query is required:
```sql
-- delete the expense, scoped to the logged-in user (ownership enforced in SQL, not just app logic)
DELETE FROM expenses WHERE id = ? AND user_id = ?
```
Before deleting, the route must first look up the row scoped to `user_id` (reusing the same `SELECT id FROM expenses WHERE id = ? AND user_id = ?` pattern from Step 8) to decide whether to 404 or proceed — `DELETE` alone can't distinguish "no such row" from "not yours" for the response.

Templates
Create: none.

Modify: `templates/profile.html` — in the "Recent Transactions" table's `Actions` column, add a "Delete" action next to the existing "Edit" link:
```html
<form method="POST" action="{{ url_for('delete_expense', id=txn['id']) }}" class="table-action-form" onsubmit="return confirm('Delete this expense?');">
    <button type="submit" class="table-action-link table-action-danger">Delete</button>
</form>
```
This requires `table-action-form` (inline layout alongside the existing "Edit" `<a>`) and `table-action-danger` (uses the existing danger/error CSS variable for text color) rules in `static/css/style.css` — no new colors, reuse whatever variable `auth-error`/similar already uses.

Files to change
`app.py` — replace the `delete_expense` stub with a real view: look up the expense scoped to `user_id`, 404 if missing, otherwise `DELETE` and redirect to `/profile`. Restrict the route to `methods=["POST"]`.
`templates/profile.html` — replace/augment the Actions cell with the Delete form alongside the Edit link.
`static/css/style.css` — add minimal styling so the Delete button matches the visual weight of the "Edit" link (no hardcoded hex values).

Files to create
None.

New dependencies
No new dependencies.

Rules for implementation
No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
Parameterised queries only — never string-format SQL, including `id`/`user_id`
Passwords hashed with werkzeug (no auth changes in this step)
Use CSS variables — never hardcode hex values
All templates extend `base.html`
No inline styles
Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
Ownership guard: the `SELECT` used to check existence and the `DELETE` itself must both filter on `user_id = ?` using the logged-in user's id — never trust the `<id>` from the URL alone
If no row matches `id` + `user_id`, return a 404 (do not distinguish "doesn't exist" from "belongs to someone else" in the response)
Route must only accept `POST` — no bare `GET` deletion
Require a confirmation step before the request is submitted (client-side `confirm()` is sufficient at this stage; no new template/page needed)
On success, redirect to `/profile` (PRG pattern)
Do not add a "confirm delete" page/template — a JS `confirm()` dialog on the existing form is sufficient for this step
Do not touch `add_expense` or `edit_expense` behavior — scope is limited to deleting existing expenses

Definition of done
- [ ] Visiting `/expenses/<id>/delete` directly with `GET` returns a 405 (method not allowed), not a deletion
- [ ] Submitting the delete form while logged out redirects to `/login`
- [ ] Submitting the delete form for an expense that belongs to another user returns a 404 and does not delete the row
- [ ] Submitting the delete form for a non-existent id returns a 404
- [ ] Submitting the delete form for your own expense removes it from the `expenses` table and redirects to `/profile`
- [ ] The deleted expense no longer appears in the profile page's transaction table, stats, or category breakdown after redirect
- [ ] Each row in the profile page's transaction table has a working "Delete" action that prompts for confirmation before submitting
- [ ] Cancelling the confirmation dialog leaves the expense untouched
- [ ] No hex colour values appear in the modified CSS — only CSS variables
