import psycopg2
import os
from deepface import DeepFace
from datetime import datetime

db_params = {
    'dbname': 'auto_attendance',
    'user': 'postgres',
    'password': 'Pragadeesh@18',
    'host': 'localhost',
    'port': '5432'
}

dataset_path = "dataset/training"

def find_person(dataset_path, img_path):
    try:
        result = DeepFace.find(img_path=img_path, db_path=dataset_path, model_name="Facenet", enforce_detection=False)
        if result and len(result) > 0:
            df = result[0]['identity']
            df = df.head(1)
            label = os.path.dirname(df.iloc[0]).split('\\')[-1]
            return label
        else:
            return "Unknown"
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

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
            # Fetch student id from Student table using name
            cursor.execute("SELECT id FROM Student WHERE name = %s", (name,))
            student_id = cursor.fetchone()

            if student_id:
                student_id = student_id[0]
                # Insert attendance record
                cursor.execute(
                    "INSERT INTO Attendance (date, subject_id, student_id, image) VALUES (%s, %s, %s, %s)",
                    (date_str, subject_id, student_id, image_path)
                )

        conn.commit()
        print("Attendance records inserted successfully.")
    except Exception as e:
        print(f"Error inserting attendance: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

new_image_path = "dataset/testing/040000_20240626.jpg"
filename = new_image_path.split("/")[-1]
nameofimg = filename.split(".")[0]
time_str = nameofimg.split("_")[0]
date_str = nameofimg.split("_")[1]

person = find_person(dataset_path, new_image_path)
if person and person != "Unknown":
    print(f"Student {person} attended class at {time_str} on {date_str}")
    insert_attendance([person], date_str, time_str, new_image_path)
else:
    print("Unable to determine the person in the image or person is Unknown.")
