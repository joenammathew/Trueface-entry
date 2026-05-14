import sqlite3

conn = sqlite3.connect('students.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS weekly_timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    branch TEXT,
    semester TEXT,
    day TEXT,

    period1 TEXT,
    period2 TEXT,
    period3 TEXT,
    period4 TEXT,
    period5 TEXT,
    period6 TEXT,
    period7 TEXT
)
""")

conn.commit()
conn.close()

print("Weekly timetable table created!")