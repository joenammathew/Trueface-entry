import cv2
import sqlite3
import winsound
from datetime import datetime

# Load face detection model
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    'haarcascade_frontalface_default.xml'
)

# Enter student name
student_name = input("Enter Student Name: ")

# Start webcam
video = cv2.VideoCapture(0)

attendance_marked = False

while True:

    # Read camera frame
    ret, frame = video.read()

    # Camera failure check
    if not ret:

        print("Camera Failed!")

        # Beep sound alert
        winsound.Beep(1000, 500)

        break

    # Convert image to grayscale
    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        1.3,
        5
    )

    # No face detected
    if len(faces) == 0:

        print("No Face Detected")

    # Face detected
    for (x, y, w, h) in faces:

        # Draw rectangle around face
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        # Mark attendance only once
        if not attendance_marked:

            # Current date and time
            now = datetime.now()

            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")

            # Connect database
            conn = sqlite3.connect(
                'students.db'
            )

            cursor = conn.cursor()

            # Insert attendance
            cursor.execute(
                '''
                INSERT INTO attendance
                (name, date, time, status)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    student_name,
                    date,
                    time,
                    "Present"
                )
            )

            conn.commit()
            conn.close()

            attendance_marked = True

            print("Attendance Marked Successfully")

            # Success beep
            winsound.Beep(1500, 400)

    # Show webcam window
    cv2.imshow(
        "Face Attendance System",
        frame
    )

    # Press q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release webcam
video.release()

# Close all windows
cv2.destroyAllWindows()