USE attendance_db;

DELIMITER $$

DROP PROCEDURE IF EXISTS add_column_if_missing$$
CREATE PROCEDURE add_column_if_missing(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table_name
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT(
            'ALTER TABLE ',
            p_table_name,
            ' ADD COLUMN ',
            p_column_name,
            ' ',
            p_column_definition
        );
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$

CALL add_column_if_missing('students', 'parent_phone', 'VARCHAR(15)')$$
CALL add_column_if_missing('students', 'parent_name', 'VARCHAR(100)')$$
DROP PROCEDURE IF EXISTS add_column_if_missing$$

DELIMITER ;

INSERT INTO users(user_id, username, password, role)
VALUES
(1, 'admin', 'admin123', 'admin'),
(2, 'teacher', 'teacher123', 'faculty')
ON DUPLICATE KEY UPDATE
username = VALUES(username),
password = VALUES(password),
role = VALUES(role);

INSERT IGNORE INTO department(department_id, department_name)
VALUES
(1, 'CSE'),
(2, 'ECE'),
(3, 'Mechanical'),
(4, 'Civil');

INSERT INTO faculty(faculty_id, faculty_name, department_id, phone, email)
VALUES
(1, 'Ramesh Rao', 1, '9999999991', 'ramesh.rao@bit.edu'),
(2, 'Anita Menon', 2, '9999999992', 'anita.menon@bit.edu'),
(3, 'Suresh Kumar', 3, '9999999993', 'suresh.kumar@bit.edu'),
(4, 'Meena Iyer', 4, '9999999994', 'meena.iyer@bit.edu')
ON DUPLICATE KEY UPDATE
faculty_name = VALUES(faculty_name),
department_id = VALUES(department_id),
phone = VALUES(phone),
email = VALUES(email);

INSERT INTO subjects(subject_id, subject_name, faculty_id)
VALUES
(1, 'Database Management Systems', 1),
(2, 'Python Programming', 1),
(3, 'Digital Electronics', 2),
(4, 'Signals and Systems', 2),
(5, 'Thermodynamics', 3),
(6, 'Structural Analysis', 4)
ON DUPLICATE KEY UPDATE
subject_name = VALUES(subject_name),
faculty_id = VALUES(faculty_id);

DELIMITER $$

DROP PROCEDURE IF EXISTS add_student$$
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
    VALUES(p_student_name, p_department_id, p_semester, p_phone, p_parent_name, p_parent_phone)
    ON DUPLICATE KEY UPDATE
    student_name = p_student_name,
    department_id = p_department_id,
    semester = p_semester,
    parent_name = p_parent_name,
    parent_phone = p_parent_phone;
END$$

DROP PROCEDURE IF EXISTS mark_attendance$$
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

DROP PROCEDURE IF EXISTS seed_20_students$$
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

DROP PROCEDURE IF EXISTS seed_attendance_sample$$
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

CALL seed_20_students();
CALL seed_attendance_sample();
