from fileinput import filename
from flask import Response
import cv2
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.utils import secure_filename
import numpy as np
import sqlite3
import os
import base64
import subprocess
import pdfplumber 
import re
import time

app = Flask(__name__)
app.secret_key = "secretkey"

def get_branch(regno):
    if "CS" in regno:
        return "CSE"
    elif "EC" in regno:
        return "ECE"
    elif "ME" in regno:
        return "MECH"
    elif "CE" in regno:
        return "CIVIL"
    return "UNKNOWN"


face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")


from datetime import datetime
import sqlite3


def mark_attendance(regno, name, branch, semester, subject):

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute("""
        SELECT * FROM attendance
        WHERE regno=? AND date=? AND subject=?
    """, (regno, today, subject))

    if cursor.fetchone():
        conn.close()
        return

    cursor.execute("""
        INSERT INTO attendance
        (regno, name, branch, semester, subject, status, date, time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        regno, name, branch, semester,
        subject, "Present", today, current_time
    ))

    conn.commit()
    conn.close()


def gen_frames():

    cam = cv2.VideoCapture(0)

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cam.isOpened():
        print("Camera error")
        return

    marked_today = set()

    while True:

        success, frame = cam.read()
        if not success:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )

        for (x, y, w, h) in faces:

            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (200, 200))

            try:
                student_id, confidence = recognizer.predict(face_roi)

                print("ID:", student_id, "Confidence:", confidence)

                if confidence < 70:

                    conn = sqlite3.connect("students.db")
                    cursor = conn.cursor()

                    # 🔥 DIRECT DB MATCH USING ID
                    cursor.execute(
                        "SELECT * FROM students WHERE id=?",
                        (int(student_id),)
                    )

                    student = cursor.fetchone()
                    conn.close()

                    if student:

                        name = student[1]
                        regno = student[3]
                        branch = student[5]
                        semester = student[6]

                        period = get_current_period()
                        subject = get_subject_from_timetable(branch, semester, period)

                        today_key = f"{regno}-{subject}-{datetime.now().date()}"

                        if today_key not in marked_today:

                            mark_attendance(regno, name, branch, semester, subject)
                            marked_today.add(today_key)

                            label = f"{name} PRESENT"

                        else:
                            label = f"{name} Already Marked"

                    else:
                        label = "Student Not Found"

                else:
                    label = "Unknown Face"

            except Exception as e:
                print("ERROR:", e)
                label = "Error"

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            cv2.putText(frame, label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
# -----------------------------
# LABEL MAP (FACE ID → REGNO)
# -----------------------------

def get_subject_from_timetable(branch, semester, period):

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT period1, period2, period3, period4, period5, period6, period7
        FROM weekly_timetable
        WHERE branch=? AND semester=? AND day=?
    """, (
        branch,
        semester,
        datetime.now().strftime("%A")
    ))

    data = cursor.fetchone()
    conn.close()

    if not data or not period:
        return "Unknown"

    mapping = {
        "period1": data[0],
        "period2": data[1],
        "period3": data[2],
        "period4": data[3],
        "period5": data[4],
        "period6": data[5],
        "period7": data[6],
    }

    return mapping.get(period, "Unknown")

# =========================
# HELPER FUNCTIONS
# =========================

from datetime import datetime

def get_current_period():
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    if "09:00" <= current_time < "10:00":
        return "period1"
    elif "10:00" <= current_time < "11:00":
        return "period2"
    elif "11:10" <= current_time < "12:10":
        return "period3"
    elif "12:10" <= current_time < "13:00":
        return "period4"
    elif "14:00" <= current_time < "15:00":
        return "period5"
    elif "15:00" <= current_time < "16:00":
        return "period6"
    else:
        return None
# Upload folders
UPLOAD_FOLDER = 'static/student_photos'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create folders automatically
os.makedirs(
    'static/student_photos',
    exist_ok=True
)

os.makedirs(
    'uploads/leave_letters',
    exist_ok=True
)

# HOME PAGE
@app.route('/')
def home():
    return render_template('index.html')

# =========================
# ADMIN LOGIN
# =========================

@app.route('/admin_login')
def admin_login():
    return render_template(
        'admin_login.html'
    )

@app.route('/admin_login_check',
           methods=['POST'])
def admin_login_check():

    username = request.form['username']
    password = request.form['password']

    if username == "admin" and password == "admin123":

        return redirect('/admin')

    else:
        flash("Invalid Admin Login")
        return redirect('/admin_login')

# =========================
# TEACHER LOGIN
# =========================
@app.route('/teacher_login')
def teacher_login():
    return render_template('teacher_login.html')

@app.route('/teacher_login_check', methods=['POST'])
def teacher_login_check():

    username = request.form['username']
    password = request.form['password']

    print("LOGIN TRY:", username, password)  # DEBUG

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM teachers
        WHERE name=? AND password=?
    """, (username.strip(), password.strip()))

    teacher = cursor.fetchone()

    print("DB RESULT:", teacher)  # DEBUG

    conn.close()

    if teacher:
        session['teacher_id'] = teacher[0]
        session['teacher_name'] = teacher[1]
        session['teacher_subject'] = teacher[2]

        return redirect('/teacher')

    else:
        flash("Invalid Teacher Login")
        return redirect('/teacher_login')
# =========================
# STUDENT LOGIN
# =========================

@app.route('/student_login_page')
def student_login_page():
    return render_template(
        'student_login.html'
    )

@app.route('/student_login', methods=['POST'])
def student_login():

    regno = request.form['regno']
    password = request.form['password']

    print("LOGIN INPUT:", regno, password)

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    all_data = cursor.fetchall()

    print("ALL STUDENTS IN DB:", all_data)

    cursor.execute("""
        SELECT * FROM students
        WHERE regno=? AND password=?
    """, (regno, password))

    student = cursor.fetchone()

    print("MATCH RESULT:", student)

    conn.close()

    if student:
        session['student_name'] = student[1]
        session['regno'] = student[3]
        return redirect('/student_dashboard')

    else:
        return "RegNo or Password not found"
    

    


@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@app.route('/reset_password', methods=['POST'])
def reset_password():

    regno = request.form['regno']
    new_password = request.form['new_password']

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM students WHERE regno=?",
        (regno,)
    )

    student = cursor.fetchone()

    if student:

        cursor.execute("""
            UPDATE students
            SET password=?
            WHERE regno=?
        """, (new_password, regno))

        conn.commit()
        conn.close()

        return "Password Updated Successfully"

    else:
        conn.close()
        return "RegNo Not Found"
    


# =========================
# STUDENT MY ATTENDANCE
# =========================

@app.route('/my_attendance')
def my_attendance():

    if 'regno' not in session:
        return redirect('/student_login_page')

    regno = session['regno']

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM attendance
        WHERE regno=?
        ORDER BY id DESC
    """, (regno,))

    data = cursor.fetchall()

    conn.close()

    return render_template(
        'my_attendance.html',
        data=data
    )
# =========================
# ADMIN DASHBOARD
# =========================

@app.route('/admin')
def admin():
    return render_template(
        'admin.html'
    )

# =========================
# TEACHER DASHBOARD
# =========================

@app.route('/teacher')
def teacher():

    if 'teacher_name' not in session:
        return redirect('/teacher_login')

    return render_template(
        'teacher.html',
        name=session['teacher_name']
    )
# =========================
# TEACHER ATTENDANCE
# =========================
@app.route('/teacher_attendance')
def teacher_attendance():

    branch = request.args.get('branch')
    semester = request.args.get('semester')
    date = request.args.get('date')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    query = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if branch and branch != "":
        query += " AND branch=?"
        params.append(branch)

    if semester and semester != "":
        query += " AND semester=?"
        params.append(semester)

    if date and date != "":
        query += " AND date=?"
        params.append(date)

    cursor.execute(query, params)
    data = cursor.fetchall()

    conn.close()

    return render_template("teacher_attendance.html", data=data)
# =========================
# ADD TEACHER
# =========================

@app.route('/add_teacher', methods=['POST'])
def add_teacher():

    name = request.form['name']
    subject = request.form['subject']
    password = request.form['password']

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO teachers (name, subject, password)
        VALUES (?, ?, ?)
    """, (name, subject, password))

    conn.commit()
    conn.close()

    return redirect('/admin')
# =========================
# DELETE TEACHER
# =========================
@app.route('/delete_teacher/<int:id>')
def delete_teacher(id):

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM teachers WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Teacher Deleted Successfully!")

    return redirect('/view_teachers')

# =========================
# VIEW TEACHER
# =========================
@app.route('/view_teachers')
def view_teachers():

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM teachers")
    data = cursor.fetchall()

    conn.close()

    return render_template('view_teachers.html', data=data)
# =========================
# STUDENT DASHBOARD
# =========================

@app.route('/student_dashboard')
def student_dashboard():

    if 'student_name' not in session:

        return redirect(
            '/student_login_page'
        )

    return render_template(
        'student_dashboard.html',
        name=session['student_name'],
        regno=session['regno']
    )




# =========================
# VIEW STUDENTS
# =========================

@app.route('/view_students')
def view_students():

    branch = request.args.get('branch')
    semester = request.args.get('semester')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if branch:
        query += " AND branch=?"
        params.append(branch)

    if semester:
        query += " AND semester=?"
        params.append(semester)

    cursor.execute(query, params)
    data = cursor.fetchall()

    conn.close()

    return render_template('view_students.html', data=data, branch=branch, semester=semester)

# =========================
# VIEW ATTENDANCE
# =========================

@app.route('/attendance')
def attendance():

    conn = sqlite3.connect(
        'students.db'
    )

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM attendance"
    )

    data = cursor.fetchall()

    conn.close()

    return render_template(
        'attendance.html',
        data=data
    )

# =========================
# UPLOAD LEAVE LETTER
# =========================
@app.route('/upload_leave', methods=['POST'])
def upload_leave():

    regno = request.form['regno']
    student_name = request.form['student_name']
    reason = request.form['reason']
    from_date = request.form['from_date']
    to_date = request.form['to_date']

    file = request.files['leave_file']
    filename = secure_filename(file.filename)

    file.save(os.path.join(UPLOAD_FOLDER, filename))

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leave_requests
        (regno, student_name, reason, from_date, to_date, filename, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        regno,
        student_name,
        reason,
        from_date,
        to_date,
        filename,
        "Pending"
    ))

    conn.commit()
    conn.close()

    return redirect('/my_leaves')

# =========================
# VIEW LEAVE REQUESTS
# =========================
@app.route('/my_leaves')
def my_leaves():

    regno = session.get('regno')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM leave_requests
        WHERE regno=?
        ORDER BY id DESC
    """, (regno,))

    data = cursor.fetchall()
    conn.close()

    return render_template('my_leaves.html', data=data)

# =========================
# ALL LEAVES (TEACHER)
# =========================
@app.route('/leave_requests')
def leave_requests():

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM leave_requests
        ORDER BY id DESC
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template('leave_requests.html', data=data)

# APPROVE
@app.route('/approve_leave/<int:id>')
def approve_leave(id):

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leave_requests
        SET status='Approved'
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/leave_requests')


# =========================
# REJECT LEAVE
# =========================

@app.route('/reject_leave/<int:id>')
def reject_leave(id):

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leave_requests
        SET status='Rejected'
        WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect('/leave_requests')

# =========================
# MANAGE SUBJECTS
# =========================

@app.route('/manage_subjects')
def manage_subjects():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects")
    data = cursor.fetchall()

    conn.close()

    return render_template("manage_subjects.html", data=data)
# =========================
#  ADD SUBJECTS
# =========================

@app.route('/add_subject', methods=['POST'])
def add_subject():
    branch = request.form['branch']
    semester = request.form['semester']
    subject_name = request.form['subject_name']
    teacher_name = request.form['teacher_name']

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO subjects(branch, semester, subject_name, teacher_name)
        VALUES (?, ?, ?, ?)
    """, (branch, semester, subject_name, teacher_name))

    conn.commit()
    conn.close()

    return redirect('/manage_subjects')

# =========================
#  FILTER SUBJECTS
# =========================
@app.route('/filter_subjects')
def filter_subjects():

    branch = request.args.get('branch')
    semester = request.args.get('semester')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM subjects
        WHERE branch=? AND semester=?
    """, (branch, semester))

    data = cursor.fetchall()
    conn.close()

    return render_template("manage_subjects.html", data=data)
# =========================
# TIMETABLE PAGE
# =========================

@app.route('/timetable')
def timetable():

    branch = request.args.get('branch')
    semester = request.args.get('semester')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    data = []

    if branch and semester:

        cursor.execute("""
            SELECT * FROM weekly_timetable
            WHERE branch=? AND semester=?
        """, (branch, semester))

        data = cursor.fetchall()

    conn.close()

    return render_template(
        'timetable.html',
        data=data,
        branch=branch,
        semester=semester
    )

# =========================
# SAVE TIMETABLE
# =========================

@app.route('/save_weekly_timetable', methods=['POST'])
def save_weekly_timetable():

    branch = request.form['branch']
    semester = request.form['semester']
    day = request.form['day']

    period1 = request.form['period1']
    period2 = request.form['period2']
    period3 = request.form['period3']
    period4 = request.form['period4']
    period5 = request.form['period5']
    period6 = request.form['period6']
    period7 = request.form['period7']

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    # check existing row

    cursor.execute("""
        SELECT * FROM weekly_timetable
        WHERE branch=? AND semester=? AND day=?
    """, (branch, semester, day))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            UPDATE weekly_timetable
            SET
            period1=?,
            period2=?,
            period3=?,
            period4=?,
            period5=?,
            period6=?,
            period7=?
            WHERE branch=? AND semester=? AND day=?
        """, (
            period1,
            period2,
            period3,
            period4,
            period5,
            period6,
            period7,
            branch,
            semester,
            day
        ))

    else:

        cursor.execute("""
            INSERT INTO weekly_timetable
            (
                branch,
                semester,
                day,
                period1,
                period2,
                period3,
                period4,
                period5,
                period6,
                period7
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            branch,
            semester,
            day,
            period1,
            period2,
            period3,
            period4,
            period5,
            period6,
            period7
        ))

    conn.commit()
    conn.close()

    return redirect(
        f'/timetable?branch={branch}&semester={semester}'
    )

# =========================
# START MONITORING
# =========================
@app.route('/start_monitoring')
def start_monitoring():
    return render_template("monitor.html")


@app.route('/monitor')
def monitor():
    return render_template("monitor.html")




from flask import Response

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

#=========================
# ADD STUDENT
#=========================
@app.route('/add_student', methods=['POST'])
def add_student():

    name = request.form['name']
    rollno = request.form['rollno']
    regno = request.form['regno']
    branch = request.form['branch']
    semester = request.form['semester']
    photo_data = request.form.get('photo_data')

    password = regno + "123"

    if not photo_data:
        flash("Capture photo first")
        return redirect('/admin')

    image_data = photo_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    filename = f"{regno}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    image = cv2.imread(filepath)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        flash("No face detected")
        return redirect('/admin')

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students (name, rollno, regno, password, branch, semester, photo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, rollno, regno, password, branch, semester, filename))

    student_id = cursor.lastrowid
    conn.commit()
    conn.close()

    os.makedirs("dataset", exist_ok=True)

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))

        for i in range(1, 11):   # more samples = better accuracy
            cv2.imwrite(f"dataset/User.{student_id}.{i}.jpg", face)

    flash("Student added successfully")
    return redirect('/admin')


# =========================
# DELETE STUDENT
# =========================
@app.route('/delete_student/<int:id>')
def delete_student(id):

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    # optional: also get photo name to delete file
    cursor.execute("SELECT photo FROM students WHERE id=?", (id,))
    data = cursor.fetchone()

    if data:
        photo = data[0]

        # delete image file
        path = os.path.join("static/student_photos", photo)
        if os.path.exists(path):
            os.remove(path)

    # delete student record
    cursor.execute("DELETE FROM students WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/view_students')




# =========================
# ATTENDANCE ANALYTICS
# =========================

@app.route('/attendance_report')
def attendance_report():

    report_type = request.args.get('type')
    value = request.args.get('value')  # date / month

    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()

    # ----------------------
    # DAILY FILTER
    # ----------------------
    if report_type == "daily":
        cursor.execute("""
            SELECT name, regno, status, date, time
            FROM attendance
            WHERE date = ?
        """, (value,))

    # ----------------------
    # MONTHLY FILTER (YYYY-MM)
    # ----------------------
    elif report_type == "monthly":
        cursor.execute("""
            SELECT name, regno, status, date, time
            FROM attendance
            WHERE substr(date, 1, 7) = ?
        """, (value,))

    # ----------------------
    # WEEKLY FILTER (LAST 7 DAYS)
    # ----------------------
    elif report_type == "weekly":
        cursor.execute("""
            SELECT name, regno, status, date, time
            FROM attendance
            WHERE date >= date('now', '-7 day')
        """)

    else:
        cursor.execute("""
            SELECT name, regno, status, date, time
            FROM attendance
        """)

    data = cursor.fetchall()
    conn.close()

    return render_template(
        'attendance_report.html',
        data=data,
        report_type=report_type
    )

# --------------------------
# BRANCH DETECTION
# --------------------------
def get_branch(regno):
    if "CS" in regno:
        return "CSE"
    elif "EC" in regno:
        return "ECE"
    elif "ME" in regno:
        return "MECH"
    elif "CE" in regno:
        return "CIVIL"
    else:
        return "UNKNOWN"



# =========================
# PDF ANALYSIS
# =========================

@app.route('/analyze_pdf', methods=['POST'])
def analyze_pdf():

    branch = request.form['branch']
    if branch == "CSE":
        branch = "CS"
    elif branch == "ECE":
        branch = "EC"
    elif branch == "MECH":
        branch = "ME"
    elif branch == "CIVIL":
        branch = "CE"
    semester = request.form['semester']

    pdf = request.files['pdf']

    filename = secure_filename(
        pdf.filename
    )

    filepath = os.path.join(
        'uploads',
        filename
    )

    pdf.save(filepath)

    extracted_data = []

    # =========================
    # TABLE HEADERS
    # =========================

    headers = [
        "Register Number",
        "Result"
    ]

    # =========================
    # EXTRACT TABLES FROM PDF
    # =========================

    with pdfplumber.open(filepath) as pdf_file:

        for page in pdf_file.pages:

            tables = page.extract_tables()

            for table in tables:

                for row in table:

                    if row:

                        clean_row = [

                            str(cell).strip()
                            if cell else ''

                            for cell in row
                        ]
                        extracted_data.append(
                            clean_row
                        )

    # =========================
    # STORE STUDENTS
    # =========================

    students = {}

    fail_keywords = [
        "F",
        "FE",
        "AB"
    ]

    # =========================
    # PROCESS EACH ROW
    # =========================

    for row in extracted_data:

        joined = ' '.join(row).upper()
        print("joined", joined)
        #temp = joined.split(" ")[0]
        # ---------------------
        # FIND REGISTER NUMBER
        # ---------------------

        reg_match = re.search(

            r'L?MEE\d{2}(' + re.escape(branch) + r')\d+',

            joined
        )
        
        if not reg_match:
            continue
        regno = reg_match.group()
        # ---------------------
        # FILTER BRANCH
        # ---------------------
        
        if branch not in regno:
            continue

        # ---------------------
        # NEW STUDENT
        # ---------------------

        if regno not in students:

            students[regno] = {

                "failed": False
            }

        # ---------------------
        # FAIL DETECTION
        # ---------------------
        print("Checking fail keywords in:", joined)
        for fail in fail_keywords:

            if fail in f' {joined} ':

                students[regno]["failed"] = True

    # =========================
    # FINAL TABLES
    # =========================

    passed_students = []

    failed_students = []

    for regno, data in students.items():

        if data["failed"]:

            failed_students.append([

                regno,
                "FAILED"

            ])

        else:

            passed_students.append([

                regno,
                "PASSED"

            ])

    # =========================
    # FINAL COUNTS
    # =========================

    total_students = len(students)

    pass_students = len(
        passed_students
    )

    fail_students = len(
        failed_students
    )

    if total_students > 0:

        pass_percentage = round(

            (pass_students / total_students) * 100,

            2
        )

    else:

        pass_percentage = 0

    # =========================
    # RENDER HTML
    # =========================

    return render_template(

        'analysis.html',

        headers=headers,

        branch=branch,

        semester=semester,

        passed_students=passed_students,

        failed_students=failed_students,

        total_students=total_students,

        pass_students=pass_students,

        fail_students=fail_students,

        pass_percentage=pass_percentage
    )


# =========================
# RUN APP
# =========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)