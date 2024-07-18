import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import psycopg2
import os
from datetime import datetime, timedelta
import schedule
import time

SMTP_HOST = 'smtp.office365.com'
SMTP_PORT = 587
SMTP_EMAIL = 'support@aptpath.in'
SMTP_PASSWORD = 'btpdcnfkgjyzdndh'


def db_connect():
    return psycopg2.connect(
        dbname="auto_attendance",
        user="postgres",
        password="Pragadeesh@18",
        host="localhost",
        port="5432"
    )


def create_daily_report(conn):
        today = datetime.now().date()
        query = f"""
        SELECT sub.name AS subject_name, 
               s.name AS student_name,
               a.image AS image_path,
               a.date AS date
        FROM attendance a
        JOIN student s ON a.student_id = s.id
        JOIN subject sub ON a.subject_id = sub.id
        WHERE a.date = '{today}'
        ORDER BY sub.name, s.name
        """
        df = pd.read_sql(query, conn)

        if not df.empty and 'subject_name' in df.columns and 'student_name' in df.columns:
            report_data = {}
            subjects = df['subject_name'].unique()
            for subject in subjects:
                report_data[subject] = df[df['subject_name'] == subject]['student_name'].tolist()

            report_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in report_data.items()]))
            daily_file_path = "daily_attendance_report.csv"
            report_df.to_csv(daily_file_path, index=False)
            return daily_file_path, df
        else:
            raise ValueError("DataFrame does not have the expected format or is empty.")


def create_monthly_report(conn):
    current_month_start = datetime.now().replace(day=1).date()
    next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)
    query = f"""
    WITH attendance_data AS (
        SELECT s.name AS student_name, 
               sub.name AS subject_name, 
               COUNT(DISTINCT a.date) AS present_count
        FROM student s
        CROSS JOIN subject sub
        LEFT JOIN attendance a ON s.id = a.student_id AND sub.id = a.subject_id
        WHERE a.date >= '{current_month_start}' AND a.date < '{next_month_start}'
        GROUP BY s.name, sub.name
    ),
    total_classes AS (
        SELECT sub.name AS subject_name, 
               COUNT(DISTINCT a.date) AS total_classes
        FROM subject sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
         WHERE a.date >= '{current_month_start}' AND a.date < '{next_month_start}'
        GROUP BY sub.name
    )
    SELECT ad.student_name AS "Student Name",
           ad.subject_name AS "Subject",
           tc.total_classes AS "Total Classes",
           ad.present_count AS "Present",
           tc.total_classes - ad.present_count AS "Absent",
           CAST((ad.present_count::float / NULLIF(tc.total_classes, 0) * 100) AS DECIMAL(5,2)) AS "Attendance %"
    FROM attendance_data ad
    JOIN total_classes tc ON ad.subject_name = tc.subject_name
    ORDER BY ad.student_name, ad.subject_name
    """
    df = pd.read_sql(query, conn)
    monthly_file_path = "monthly_attendance_report.csv"
    df.to_csv(monthly_file_path, index=False)
    return monthly_file_path


def fetch_professor_emails(conn):
    query = """
    SELECT name, email
    FROM faculty
    """
    df = pd.read_sql(query, conn)
    return dict(zip(df.name, df.email))


def dispatch_email(subject, body_content, recipient, cc_list, attachments):
    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = recipient
    msg['Cc'] = cc_list
    msg['Subject'] = subject

    msg.attach(MIMEText(body_content, 'html'))

    for attachment in attachments:
        attach_file = MIMEBase('application', 'octet-stream')
        with open(attachment, 'rb') as file:
            attach_file.set_payload(file.read())
        encoders.encode_base64(attach_file)
        attach_file.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment)}')
        msg.attach(attach_file)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        recipients = [recipient] + cc_list.split(', ')
        server.sendmail(SMTP_EMAIL, recipients, msg.as_string())

    print(f"Email sent successfully to {recipient} with CC to {cc_list}")


def create_and_dispatch_daily_reports():
    conn = db_connect()

    daily_report, daily_data = create_daily_report(conn)

    professor_emails = fetch_professor_emails(conn)

    images = []
    for _, row in daily_data.iterrows():
        path = row['image_path']
        images.append(path)

    dispatch_email(
        subject="Daily Attendance Report - All Subjects",
        body_content="<p>Please find the attached daily attendance report for all subjects.</p>",
        recipient='pragadeesh0218@gmail.com',
        cc_list=', '.join(professor_emails.values()),
        attachments=[daily_report] + images
    )

    conn.close()


def create_and_dispatch_monthly_reports():
    conn = db_connect()

    monthly_report = create_monthly_report(conn)

    professor_emails = fetch_professor_emails(conn)

    dispatch_email(
        subject="Monthly Attendance Report",
        body_content="<p>Please find the attached monthly attendance report.</p>",
        recipient='pragadeesh0218@gmail.com',
        cc_list=', '.join(professor_emails.values()),
        attachments=[monthly_report]
    )

    conn.close()

current_time = datetime.now()
daily_schedule_time = "18:00"
schedule.every().day.at(daily_schedule_time).do(create_and_dispatch_daily_reports)

def is_last_day_of_month():
    today = datetime.now()
    next_day = today + timedelta(days=1)
    return today.month != next_day.month
schedule.every().day.at("18:00").do(lambda: create_and_dispatch_monthly_reports() if is_last_day_of_month() else None)

while True:
    schedule.run_pending()
    time.sleep(60)