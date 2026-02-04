import os, sqlite3

DB_PATH = os.path.join("instance", "smartfactory.db")
SCHEMA_PATH = os.path.join("app", "schema.sql")

os.makedirs("instance", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    conn.executescript(f.read())
conn.commit()
conn.close()

print("DB initialized:", DB_PATH)
