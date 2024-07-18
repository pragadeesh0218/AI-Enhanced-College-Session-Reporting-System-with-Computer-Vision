from deepface import DeepFace
import os
import numpy as np
import psycopg2
from datetime import datetime

db_params = {
    'dbname': 'auto_attendance',
    'user': 'postgres',
    'password': 'Pragadeesh@18',
    'host': 'localhost',
    'port': '5432'
}

def insert_attendance(names, date_str, time_str, image_path):
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        formatted_time_str = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
        time_obj = datetime.strptime(formatted_time_str, '%H:%M:%S').time()

        cursor.execute("SELECT id FROM Subject WHERE from_time = %s", (time_obj,))
        subject_id = cursor.fetchone()
        if not subject_id:
            print("No subject found for the given time.")
            return
        subject_id = subject_id[0]

        for name in names:
            cursor.execute("SELECT id FROM Student WHERE name = %s", (name,))
            student_id = cursor.fetchone()
            if student_id:
                student_id = student_id[0]

                cursor.execute(
                    "INSERT INTO Attendance (date, subject_id, student_id, image) VALUES (%s, %s, %s, %s)",
                    (date_str, subject_id, student_id, image_path)
                )

        conn.commit()
        cursor.close()
        conn.close()
        print("Attendance records inserted successfully.")
    except Exception as e:
        print(f"Error inserting attendance: {e}")

image_path = "dataset/testing/group/020000_20240626.jpg"
dataset_path = "dataset/training"

faces = DeepFace.extract_faces(img_path=image_path)
print(f"Number of faces detected: {len(faces)}")
extracted_faces = []
names = []

for face in faces:
    face_image = face['face']
    extracted_faces.append(face_image)

for i, face_image in enumerate(extracted_faces):
    face_image_array = np.array(face_image)

    result = DeepFace.find(img_path=face_image_array, db_path=dataset_path, enforce_detection=False)
    print(f"Results for face {i + 1}:")
    if result and len(result) > 0:
        df = result[0]['identity']
        df = df.head(1)
        label = os.path.dirname(df.iloc[0]).split('\\')[-1]  # Extract label from the path
        print(label)
        names.append(label)
    else:
        print("Unknown")

filename = image_path.split("/")[-1]
nameofimg = filename.split(".")[0]
time_str = nameofimg.split("_")[0]
date_str = nameofimg.split("_")[1]
print(f"student {names} attended class at {time_str} on {date_str}")

insert_attendance(names, date_str, time_str, image_path)
