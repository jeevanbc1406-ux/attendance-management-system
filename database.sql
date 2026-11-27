DROP DATABASE IF EXISTS attendance_db;
CREATE DATABASE attendance_db;
USE attendance_db;

CREATE TABLE users(
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    CONSTRAINT users_role_chk CHECK (role IN ('admin', 'faculty', 'student'))
);

CREATE TABLE department(
    department_id INT PRIMARY KEY AUTO_INCREMENT,
    department_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE students(
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    student_name VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    semester INT NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    parent_name VARCHAR(100),
    parent_phone VARCHAR(15),
    CONSTRAINT students_semester_chk CHECK (semester BETWEEN 1 AND 8),
    FOREIGN KEY(department_id)
    REFERENCES department(department_id)
);

CREATE TABLE faculty(
    faculty_id INT PRIMARY KEY AUTO_INCREMENT,
    faculty_name VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    FOREIGN KEY(department_id)
    REFERENCES department(department_id)
);

CREATE TABLE subjects(
    subject_id INT PRIMARY KEY AUTO_INCREMENT,
    subject_name VARCHAR(100) NOT NULL UNIQUE,
    faculty_id INT NOT NULL,
    FOREIGN KEY(faculty_id)
    REFERENCES faculty(faculty_id)
);

CREATE TABLE attendance(
    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    date DATE NOT NULL,
    status VARCHAR(10) NOT NULL,
    CONSTRAINT attendance_student_subject_date_uk UNIQUE(student_id, subject_id, date),
    CONSTRAINT attendance_status_chk CHECK (status IN ('Present', 'Absent')),
    FOREIGN KEY(student_id)
    REFERENCES students(student_id),
    FOREIGN KEY(subject_id)
    REFERENCES subjects(subject_id)
);

CREATE VIEW attendance_summary AS
SELECT
    attendance.student_id,
    attendance.subject_id,
    COUNT(*) AS total_classes,
    SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) AS present_classes,
    ROUND(
        SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) * 100 / COUNT(*),
        2
    ) AS attendance_percentage
FROM attendance
GROUP BY attendance.student_id, attendance.subject_id;

CREATE VIEW attendance_warning AS
SELECT
    ROW_NUMBER() OVER (ORDER BY student_id, subject_id) AS warning_id,
    student_id,
    subject_id,
    attendance_percentage,
    'Attendance below 75%' AS warning_message
FROM attendance_summary
WHERE attendance_percentage < 75;

DELIMITER $$

CREATE PROCEDURE add_student(
    IN p_student_name VARCHAR(100),
    IN p_department_id INT,
    IN p_semester INT,
    IN p_phone VARCHAR(15),
    IN p_parent_name VARCHAR(100),
    IN p_parent_phone VARCHAR(15)
)
BEGIN
    INSERT INTO students(student_name, department_id, semester, phone, parent_name, parent_phone)
    VALUES(p_student_name, p_department_id, p_semester, p_phone, p_parent_name, p_parent_phone);
END$$

CREATE PROCEDURE mark_attendance(
    IN p_student_id INT,
    IN p_subject_id INT,
    IN p_date DATE,
    IN p_status VARCHAR(10)
)
BEGIN
    INSERT INTO attendance(student_id, subject_id, date, status)
    VALUES(p_student_id, p_subject_id, p_date, p_status)
    ON DUPLICATE KEY UPDATE status = p_status;
END$$

CREATE PROCEDURE seed_20_students()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE dept_id INT;
    DECLARE sem_value INT;
    DECLARE phone_value VARCHAR(15);
    DECLARE student_value VARCHAR(100);
    DECLARE parent_value VARCHAR(100);

    WHILE i <= 20 DO
        SET dept_id = ((i - 1) MOD 4) + 1;
        SET sem_value = ((i - 1) MOD 8) + 1;
        SET phone_value = CONCAT('900000', LPAD(i, 4, '0'));
        SET student_value = CASE i
            WHEN 1 THEN 'Aarav'
            WHEN 2 THEN 'Ananya'
            WHEN 3 THEN 'Rohan'
            WHEN 4 THEN 'Priya'
            WHEN 5 THEN 'Vikram'
            WHEN 6 THEN 'Sneha'
            WHEN 7 THEN 'Rahul'
            WHEN 8 THEN 'Meera'
            WHEN 9 THEN 'Kiran'
            WHEN 10 THEN 'Pooja'
            WHEN 11 THEN 'Aditya'
            WHEN 12 THEN 'Neha'
            WHEN 13 THEN 'Arjun'
            WHEN 14 THEN 'Kavya'
            WHEN 15 THEN 'Sanjay'
            WHEN 16 THEN 'Divya'
            WHEN 17 THEN 'Nikhil'
            WHEN 18 THEN 'Asha'
            WHEN 19 THEN 'Manoj'
            WHEN 20 THEN 'Riya'
        END;
        SET parent_value = CASE i
            WHEN 1 THEN 'Rajesh Sharma'
            WHEN 2 THEN 'Sunita Iyer'
            WHEN 3 THEN 'Mahesh Verma'
            WHEN 4 THEN 'Lakshmi Nair'
            WHEN 5 THEN 'Prakash Rao'
            WHEN 6 THEN 'Geetha Menon'
            WHEN 7 THEN 'Sanjay Patel'
            WHEN 8 THEN 'Anita Reddy'
            WHEN 9 THEN 'Ramesh Kumar'
            WHEN 10 THEN 'Kavitha Singh'
            WHEN 11 THEN 'Vijay Mehta'
            WHEN 12 THEN 'Deepa Joshi'
            WHEN 13 THEN 'Mohan Das'
            WHEN 14 THEN 'Rekha Shetty'
            WHEN 15 THEN 'Harish Gupta'
            WHEN 16 THEN 'Latha Krishnan'
            WHEN 17 THEN 'Suresh Bhat'
            WHEN 18 THEN 'Meena Kulkarni'
            WHEN 19 THEN 'Gopal Jain'
            WHEN 20 THEN 'Nandini Rao'
        END;

        CALL add_student(
            student_value,
            dept_id,
            sem_value,
            phone_value,
            parent_value,
            CONCAT('910000', LPAD(i, 4, '0'))
        );

        SET i = i + 1;
    END WHILE;
END$$

CREATE PROCEDURE seed_attendance_sample()
BEGIN
    DECLARE i INT DEFAULT 1;

    WHILE i <= 20 DO
        CALL mark_attendance(i, ((i - 1) MOD 6) + 1, '2026-06-01', 'Present');
        CALL mark_attendance(i, ((i - 1) MOD 6) + 1, '2026-06-02', 'Present');

        IF i MOD 3 = 0 THEN
            CALL mark_attendance(i, ((i - 1) MOD 6) + 1, '2026-06-03', 'Absent');
        ELSE
            CALL mark_attendance(i, ((i - 1) MOD 6) + 1, '2026-06-03', 'Present');
        END IF;

        SET i = i + 1;
    END WHILE;
END$$

DELIMITER ;

INSERT INTO users(username, password, role)
VALUES
('admin', 'admin123', 'admin'),
('teacher', 'teacher123', 'faculty');

INSERT INTO department(department_name)
VALUES
('CSE'),
('ECE'),
('Mechanical'),
('Civil');

INSERT INTO faculty(faculty_name, department_id, phone, email)
VALUES
('Ramesh Rao', 1, '9999999991', 'ramesh.rao@bit.edu'),
('Anita Menon', 2, '9999999992', 'anita.menon@bit.edu'),
('Suresh Kumar', 3, '9999999993', 'suresh.kumar@bit.edu'),
('Meena Iyer', 4, '9999999994', 'meena.iyer@bit.edu');

INSERT INTO subjects(subject_name, faculty_id)
VALUES
('Database Management Systems', 1),
('Python Programming', 1),
('Digital Electronics', 2),
('Signals and Systems', 2),
('Thermodynamics', 3),
('Structural Analysis', 4);

CALL seed_20_students();
CALL seed_attendance_sample();
