import sqlite3
import os

db_path = os.path.join('d:\\antigravity FYP 2', 'db.sqlite3')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables in DB:")
    for t in tables:
        print(t[0])
    
    # check if django_migrations has anything
    migrations = conn.execute("SELECT app, name FROM django_migrations;").fetchall()
    print("\nMigrations applied:")
    for m in migrations:
        print(m)
else:
    print("No db.sqlite3 found")
