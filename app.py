
from functools import wraps
import os

from flask import Flask, abort, flash, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ['MYSQL_USER']
app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_PASSWORD']
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'attendance_db')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', '3307'))

mysql = MySQL(app)


def login_required(allowed_roles=None):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user_role = session.get('role')
            if not user_role:
                return redirect(url_for('login'))

            if allowed_roles and user_role not in allowed_roles:
                if user_role == 'student':
                    return redirect(url_for('student_dashboard'))
                return redirect(url_for('dashboard'))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def ensure_student_parent_columns():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'students'
          AND COLUMN_NAME = 'parent_phone'
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE students ADD COLUMN parent_phone VARCHAR(15) NULL")
        mysql.connection.commit()

    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'students'
          AND COLUMN_NAME = 'parent_name'
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE students ADD COLUMN parent_name VARCHAR(100) NULL")
        mysql.connection.commit()

def ensure_reference_tables():
    cur = mysql.connection.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS department(
            department_id INT PRIMARY KEY AUTO_INCREMENT,
            department_name VARCHAR(100) NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faculty(
            faculty_id INT PRIMARY KEY AUTO_INCREMENT,
            faculty_name VARCHAR(100) NOT NULL,
            department_id INT NOT NULL,
            phone VARCHAR(15) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            FOREIGN KEY(department_id)
            REFERENCES department(department_id)
        )
    """)
    cur.execute("SELECT COUNT(*) FROM department")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO department(department_name) VALUES(%s)", ('CSE',))
    mysql.connection.commit()
    ensure_student_parent_columns()

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'faculty')
        username = request.form['username'].strip()
        password = request.form['password']

        cur = mysql.connection.cursor()
        session.clear()

        if login_type == 'student':
            cur.execute(
                """
                SELECT student_id, student_name, password_hash
                FROM students
                WHERE student_id=%s
                """,
                (username,)
            )
            student = cur.fetchone()
            if student and student[2] and check_password_hash(student[2], password):
                session['role'] = 'student'
                session['student_id'] = student[0]
                session['name'] = student[1]
                return redirect(url_for('student_dashboard'))
        elif login_type in {'admin', 'faculty'}:
            cur.execute(
                "SELECT user_id, username, role, password_hash, faculty_id FROM users WHERE username=%s AND role=%s",
                (username, login_type)
            )

            user = cur.fetchone()

            if user and check_password_hash(user[3], password):
                if user[2] == 'faculty' and user[4] is None:
                    error = 'This faculty login is not linked to a faculty record.'
                    return render_template('login.html', error=error), 403
                session['role'] = user[2]
                session['user_id'] = user[0]
                session['name'] = user[1]
                if user[2] == 'faculty':
                    session['faculty_id'] = user[4]
                return redirect(url_for('dashboard'))

        error = 'Invalid login details. Please check your role, username, and password.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required({'admin', 'faculty'})
def dashboard():
    return render_template('dashboard.html')


@app.route('/students', methods=['GET', 'POST'])
@login_required({'admin'})
def students():
    cur = mysql.connection.cursor()
    ensure_reference_tables()
    ensure_student_parent_columns()

    if request.method == 'POST':
        name = request.form['student_name']
        semester = request.form['semester']
        department_id = request.form['department_id']
        phone = request.form['phone']
        parent_name = request.form['parent_name']
        parent_phone = request.form['parent_phone']
        student_password = request.form['student_password']
        if len(student_password) < 8:
            return 'Student passwords must be at least 8 characters long.', 400

        cur.execute(
            """
            INSERT INTO students(student_name, department_id, semester, phone, parent_name, parent_phone, password_hash)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            """,
            (name, department_id, semester, phone, parent_name, parent_phone, generate_password_hash(student_password))
        )

        mysql.connection.commit()

    cur.execute("""
        SELECT
            student_id,
            student_name,
            department_id,
            semester,
            phone,
            parent_name,
            parent_phone
        FROM students
        ORDER BY student_id
    """)
    student_data = cur.fetchall()

    return render_template('students.html', students=student_data)


@app.route('/faculty', methods=['GET', 'POST'])
@login_required({'admin'})
def faculty():
    ensure_reference_tables()
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        faculty_name = request.form['faculty_name']
        department_id = request.form['department_id']
        phone = request.form['phone']
        email = request.form['email']

        cur.execute(
            "INSERT INTO faculty(faculty_name, department_id, phone, email) VALUES(%s,%s,%s,%s)",
            (faculty_name, department_id, phone, email)
        )

        mysql.connection.commit()

    cur.execute("SELECT * FROM department")
    departments = cur.fetchall()

    cur.execute("""
        SELECT
            faculty.faculty_id,
            faculty.faculty_name,
            department.department_name,
            faculty.phone,
            faculty.email
        FROM faculty
        LEFT JOIN department
        ON faculty.department_id = department.department_id
    """)
    faculty_data = cur.fetchall()

    return render_template(
        'faculty.html',
        faculty=faculty_data,
        departments=departments
    )


@app.route('/subjects', methods=['GET', 'POST'])
@login_required({'admin'})
def subjects():
    ensure_reference_tables()
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        subject_name = request.form['subject_name']
        faculty_id = request.form['faculty_id']

        cur.execute(
            "INSERT INTO subjects(subject_name, faculty_id) VALUES(%s,%s)",
            (subject_name, faculty_id)
        )

        mysql.connection.commit()

    cur.execute("SELECT * FROM faculty")
    faculty_data = cur.fetchall()

    cur.execute("""
        SELECT
            subjects.subject_id,
            subjects.subject_name,
            faculty.faculty_name,
            department.department_name
        FROM subjects
        LEFT JOIN faculty
        ON subjects.faculty_id = faculty.faculty_id
        LEFT JOIN department
        ON faculty.department_id = department.department_id
    """)
    subject_data = cur.fetchall()

    return render_template(
        'subjects.html',
        subjects=subject_data,
        faculty=faculty_data
    )


@app.route('/attendance', methods=['GET', 'POST'])
@login_required({'admin', 'faculty'})
def attendance():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM students")
    students = cur.fetchall()

    if session['role'] == 'admin':
        cur.execute("SELECT * FROM subjects")
    else:
        faculty_id = linked_faculty_id(cur)
        cur.execute("SELECT * FROM subjects WHERE faculty_id=%s", (faculty_id,))
    subjects = cur.fetchall()

    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        date = request.form['date']
        status = request.form['status']

        if session['role'] == 'faculty':
            faculty_id = linked_faculty_id(cur)
            cur.execute(
                "SELECT 1 FROM subjects WHERE subject_id=%s AND faculty_id=%s",
                (subject_id, faculty_id),
            )
            if cur.fetchone() is None:
                abort(403)

        cur.execute(
            """
            INSERT INTO attendance(student_id, subject_id, date, status)
            VALUES(%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """,
            (student_id, subject_id, date, status)
        )

        mysql.connection.commit()
        flash('Attendance saved successfully.', 'success')
        return redirect(url_for('attendance'))

    return render_template(
        'attendance.html',
        students=students,
        subjects=subjects
    )


@app.route('/reports')
@login_required({'admin', 'faculty'})
def reports():
    cur = mysql.connection.cursor()
    ensure_student_parent_columns()

    report_scope = ''
    warning_scope = ''
    query_args = ()
    if session['role'] == 'faculty':
        faculty_id = linked_faculty_id(cur)
        report_scope = 'WHERE subjects.faculty_id = %s'
        warning_scope = 'WHERE subjects.faculty_id = %s'
        query_args = (faculty_id,)

    cur.execute(f"""
        SELECT
            attendance.student_id,
            students.student_name,
            subjects.subject_name,
            COUNT(CASE WHEN status='Present' THEN 1 END)*100/COUNT(*) AS percentage
        FROM attendance
        JOIN students
        ON attendance.student_id = students.student_id
        JOIN subjects
        ON attendance.subject_id = subjects.subject_id
        {report_scope}
        GROUP BY attendance.student_id, students.student_name, subjects.subject_name
        ORDER BY attendance.student_id, subjects.subject_name
    """, query_args)

    report_data = cur.fetchall()

    cur.execute(f"""
        SELECT
            attendance_warning.warning_id,
            attendance_warning.student_id,
            students.student_name,
            subjects.subject_name,
            students.parent_name,
            students.parent_phone,
            attendance_warning.attendance_percentage,
            CONCAT(
                attendance_warning.warning_message,
                '. Please inform parent/guardian for ',
                students.student_name,
                '.'
            ) AS warning_message
        FROM attendance_warning
        JOIN students
        ON attendance_warning.student_id = students.student_id
        JOIN subjects
        ON attendance_warning.subject_id = subjects.subject_id
        {warning_scope}
        ORDER BY attendance_warning.warning_id DESC
    """, query_args)

    warnings = cur.fetchall()

    return render_template(
        'reports.html',
        reports=report_data,
        warnings=warnings
    )


@app.route('/student-dashboard')
@login_required({'student'})
def student_dashboard():
    cur = mysql.connection.cursor()
    ensure_student_parent_columns()
    student_id = session['student_id']

    cur.execute("""
        SELECT
            students.student_id,
            students.student_name,
            students.semester,
            department.department_name,
            students.phone,
            students.parent_name,
            students.parent_phone
        FROM students
        LEFT JOIN department
        ON students.department_id = department.department_id
        WHERE students.student_id = %s
    """, (student_id,))
    student = cur.fetchone()

    cur.execute("""
        SELECT
            subjects.subject_name,
            attendance_summary.total_classes,
            attendance_summary.present_classes,
            attendance_summary.attendance_percentage
        FROM attendance_summary
        JOIN subjects
        ON attendance_summary.subject_id = subjects.subject_id
        WHERE attendance_summary.student_id = %s
        ORDER BY subjects.subject_name
    """, (student_id,))
    reports = cur.fetchall()

    cur.execute("""
        SELECT
            subjects.subject_name,
            attendance_warning.attendance_percentage,
            students.parent_name,
            students.parent_phone,
            CONCAT(
                attendance_warning.warning_message,
                '. Please inform parent/guardian for ',
                students.student_name,
                '.'
            ) AS warning_message
        FROM attendance_warning
        JOIN subjects
        ON attendance_warning.subject_id = subjects.subject_id
        JOIN students
        ON attendance_warning.student_id = students.student_id
        WHERE attendance_warning.student_id = %s
        ORDER BY subjects.subject_name
    """, (student_id,))
    warnings = cur.fetchall()

    return render_template(
        'student_dashboard.html',
        student=student,
        reports=reports,
        warnings=warnings
    )


def linked_faculty_id(cursor):
    """Return the faculty record linked to the signed-in faculty account."""
    cursor.execute(
        "SELECT faculty_id FROM users WHERE user_id=%s AND role='faculty'",
        (session.get('user_id'),),
    )
    row = cursor.fetchone()
    if row is None or row[0] is None or row[0] != session.get('faculty_id'):
        abort(403)
    return row[0]


if __name__ == '__main__':
    app.run(debug=True)
