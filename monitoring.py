import cv2
import sqlite3
from datetime import datetime
import os

# -----------------------
# FACE DETECTOR
# -----------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# -----------------------
# LOAD MODEL
# -----------------------
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")

# -----------------------
# STUDENTS DATA
# -----------------------
conn = sqlite3.connect("students.db")
cursor = conn.cursor()

cursor.execute("SELECT id, name, regno, branch, semester FROM students")
students = cursor.fetchall()

student_map = {}

for s in students:
    student_map[s[0]] = {
        "name": s[1],
        "regno": s[2],
        "branch": s[3],
        "semester": s[4]
    }

# -----------------------
# CAMERA
# -----------------------
cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("Camera error")
    exit()

print("Monitoring started...")

conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

# -----------------------
# LOOP
# -----------------------
while True:

    ret, frame = cam.read()
    if not ret:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:

        face = gray[y:y+h, x:x+w]

        if face.size == 0:
            continue

        label, confidence = recognizer.predict(face)

        name = "Unknown"

        if confidence < 60 and label in student_map:

            student = student_map[label]

            name = student["name"]
            regno = student["regno"]
            branch = student["branch"]
            semester = student["semester"]

            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time_now = now.strftime("%H:%M:%S")

            cursor.execute("""
                SELECT * FROM attendance
                WHERE regno=? AND date=?
            """, (regno, date))

            if not cursor.fetchone():

                cursor.execute("""
                    INSERT INTO attendance
                    (name, regno, branch, semester, status, date, time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, regno, branch, semester,
                    "Present", date, time_now
                ))

                conn.commit()

                print("Marked:", name)

        # BOX
        color = (0,255,0) if name != "Unknown" else (0,0,255)

        cv2.rectangle(frame, (x,y), (x+w,y+h), color, 2)
        cv2.putText(frame, name, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imshow("Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cam.release()
cv2.destroyAllWindows()
conn.close()