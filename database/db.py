import os
import sqlite3

from werkzeug.security import generate_password_hash

# Anchor to the project root (one level up from this file), so the path
# resolves correctly regardless of the cwd `python app.py` is run from.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
# Autocomplete suggestions only — account type is free text, not a fixed set.
ACCOUNT_TYPES = ["Cash", "Wallet", "Bank"]
PAYMENT_METHODS = ["Cash", "Card", "UPI"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'Cash',
            date TEXT NOT NULL,
            description TEXT,
            account_id INTEGER REFERENCES accounts (id),
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()}
    if "account_id" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN account_id INTEGER REFERENCES accounts (id)")
    if "payment_method" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Cash'")

    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    if row["count"] > 0:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    # Starting balances are seeded post-deduction: each already accounts for
    # the one sample expense below that's linked to it.
    cash_id = conn.execute(
        "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
        (user_id, "Cash", "Cash", 4550.00),
    ).lastrowid
    wallet_id = conn.execute(
        "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
        (user_id, "Wallet", "Wallet", 880.00),
    ).lastrowid
    bank_id = conn.execute(
        "INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
        (user_id, "HDFC Bank", "Bank", 18500.00),
    ).lastrowid

    sample_expenses = [
        (user_id, 450.00, "Food", "2026-07-01", "Groceries for the week", "Cash", cash_id),
        (user_id, 120.00, "Transport", "2026-07-02", "Auto fare", "UPI", wallet_id),
        (user_id, 1500.00, "Bills", "2026-07-03", "Electricity bill", "Card", bank_id),
        (user_id, 800.00, "Health", "2026-07-05", "Pharmacy", "Card", None),
        (user_id, 600.00, "Entertainment", "2026-07-08", "Movie tickets", "UPI", None),
        (user_id, 2200.00, "Shopping", "2026-07-12", "New shoes", "Card", None),
        (user_id, 250.00, "Other", "2026-07-15", "Miscellaneous", "Cash", None),
        (user_id, 350.00, "Food", "2026-07-20", "Dinner with friends", "UPI", None),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description, payment_method, account_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        sample_expenses,
    )
    conn.commit()
    conn.close()
