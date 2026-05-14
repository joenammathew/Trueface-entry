import sqlite3

conn = sqlite3.connect('students.db')
cursor = conn.cursor()

# =========================
# STUDENTS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    rollno TEXT,
    regno TEXT UNIQUE,
    password TEXT,
    branch TEXT,
    semester TEXT,
    photo TEXT
)
""")

# =========================
# ATTENDANCE TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regno TEXT,
    name TEXT,
    branch TEXT,
    semester TEXT,
    subject TEXT,
    status TEXT,
    date TEXT,
    time TEXT
)
""")

# =========================
# LEAVE REQUESTS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regno TEXT,
    student_name TEXT,
    reason TEXT,
    from_date TEXT,
    to_date TEXT,
    filename TEXT,
    status TEXT
)
""")

# =========================
# TEACHERS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    subject TEXT,
    password TEXT
)
""")

# =========================
# SUBJECTS TABLE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch TEXT,
    semester TEXT,
    subject_name TEXT,
    teacher_name TEXT
)
""")

# =========================
# TIMETABLE TABLE (🔥 IMPORTANT - YOU WERE MISSING THIS)
# =========================
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

print("Database Ready Successfully")