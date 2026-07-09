description	Seed realistic dummy expenses for every user in the database
argument-hint	<count> <months>
allowed-tools	Read, Bash(python3:*)
Read database/db.py to understand the expenses table schema, the db connection pattern, and the database file name.

User input: $ARGUMENTS

Step 1 — Parse arguments
Extract from $ARGUMENTS:

count — integer, number of expenses to create per user
months — integer, how many past months to spread them across
If either argument is missing or not a valid integer, stop and say: "Usage: /seed-all-expenses <count> <months> Example: /seed-all-expenses 50 6"

Step 2 — Verify users exist
Before generating anything, fetch all user ids from the users table. If there are none, stop and say: "No users found in the database."

Step 3 — Generate and insert expenses for every user
Write and run a single Python script that, for each user id found in Step 2:

Spreads that user's expenses randomly across the past months
Uses these categories with realistic Indian descriptions and amounts (₹):
Food: 50–800
Transport: 20–500
Bills: 200–3000
Health: 100–2000
Entertainment: 100–1500
Shopping: 200–5000
Other: 50–1000
Distributes categories roughly proportionally (Food most common, Health and Entertainment least)
Uses the db connection pattern from db.py — do not hardcode the database filename
Uses parameterised queries only — no string formatting in SQL
Inserts all expenses for all users in a single transaction — roll back everything for every user if any single insert fails

Step 4 — Confirm
Print:

How many users were seeded and the total number of expenses inserted
A per-user breakdown: user_id — count inserted
The overall date range they span
A sample of 5 inserted records across the whole run
