import cv2
import os
import numpy as np
import sqlite3

recognizer = cv2.face.LBPHFaceRecognizer_create()
face_samples = []
labels = []

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

cursor.execute("SELECT id FROM students")
ids = cursor.fetchall()
conn.close()

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

for (id,) in ids:

    for img_path in os.listdir("dataset"):

        if img_path.startswith(f"User.{id}."):

            img = cv2.imread("dataset/" + img_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(gray)

            for (x, y, w, h) in faces:
                face_samples.append(gray[y:y+h, x:x+w])
                labels.append(int(id))

recognizer.train(face_samples, np.array(labels))
recognizer.save("trainer.yml")

print("Training Completed Successfully")