# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This is **Spendly**, a Flask expense-tracker app being built incrementally as a step-by-step learning exercise. Placeholder routes and files are annotated with `# Step N` comments (e.g. `app.py`, `database/db.py`) indicating what will be implemented next and in what order. When asked to "implement the next step" or similar, check these comments/placeholder return values (e.g. `"Logout — coming in Step 3"`) to figure out current progress and what belongs in that step. Don't jump ahead and build later-step functionality unless asked.

Current state: routes for landing/register/login/terms/privacy render real templates; `logout`, `profile`, and the `/expenses/*` CRUD routes are stubs returning placeholder strings; `database/db.py` is not yet implemented (it's just a comment describing the expected `get_db()` / `init_db()` / `seed_db()` functions).

## Commands

Run these from the `expense-tracker/` project root (where `app.py` lives).

```bash
# activate the venv (Windows)
venv\Scripts\activate

# install deps
pip install -r requirements.txt

# run the dev server (http://localhost:5001)
python app.py

# run tests
pytest
```

There is no lint/format tooling configured in this repo yet.

## Architecture

- **`app.py`** — single-file Flask app; all routes are defined directly on `app` (no blueprints). `debug=True`, runs on port `5001`.
- **`database/db.py`** — intended to be the sole database access point: a SQLite connection helper (`get_db()` with `row_factory` and foreign keys enabled), schema creation (`init_db()`, using `CREATE TABLE IF NOT EXISTS`), and dev seed data (`seed_db()`). Routes should go through these functions rather than opening their own connections.
- **`templates/`** — Jinja2 templates, all extending `templates/base.html` (nav, footer, `{% block title %}` / `{% block content %}` / `{% block scripts %}`). Static assets are referenced via `url_for('static', filename=...)`.
- **`static/css/style.css`** — shared site styling; `static/css/landing.css` — landing-page-specific styling.
- **`static/js/main.js`** — currently empty; JS is added here as features require it (no build step/bundler — plain script tag included from `base.html`).
- Branding: product name is "Spendly", tagline "Track every rupee. Own your finances." (currency/audience context is INR).
