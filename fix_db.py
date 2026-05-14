import sqlite3

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    subject TEXT,
    password TEXT
)
""")

conn.commit()
conn.close()

print("Teachers table created successfully")