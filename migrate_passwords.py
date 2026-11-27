"""Hash legacy account passwords and assign initial passwords to students.

Run against the existing database after configuring the MYSQL_* environment
variables. Student credentials are written to a new CSV file chosen by the
operator; distribute them privately and delete the file after delivery.
"""

import argparse
import csv
import secrets
from pathlib import Path

import MySQLdb
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app import app


def columns(cursor, table):
    cursor.execute(
        """SELECT COLUMN_NAME FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s""",
        (table,),
    )
    return {row[0] for row in cursor.fetchall()}


def is_werkzeug_hash(value):
    return isinstance(value, str) and value.startswith(('scrypt:', 'pbkdf2:'))


def migrate(credentials_path):
    credentials_path = Path(credentials_path).expanduser().resolve()
    try:
        credentials_path.relative_to(Path(__file__).resolve().parent)
    except ValueError:
        pass
    else:
        raise ValueError('Choose a credential CSV destination outside the project folder')
    if credentials_path.exists():
        raise FileExistsError(f"Refusing to overwrite {credentials_path}")

    connection = MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        port=app.config['MYSQL_PORT'],
        charset='utf8mb4',
    )
    generated = []
    credentials_file_created = False
    try:
        cursor = connection.cursor()
        user_columns = columns(cursor, 'users')
        student_columns = columns(cursor, 'students')

        if 'password_hash' not in user_columns:
            cursor.execute('ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL')
        if 'password' in user_columns:
            cursor.execute('SELECT user_id, password, password_hash FROM users')
            for user_id, legacy_password, existing_hash in cursor.fetchall():
                if not existing_hash:
                    if not legacy_password:
                        raise ValueError(f'User {user_id} has no password to migrate')
                    cursor.execute(
                        'UPDATE users SET password_hash=%s WHERE user_id=%s',
                        (generate_password_hash(legacy_password), user_id),
                    )
            cursor.execute('ALTER TABLE users DROP COLUMN password')
        cursor.execute('ALTER TABLE users MODIFY password_hash VARCHAR(255) NOT NULL')

        if 'password_hash' not in student_columns:
            cursor.execute('ALTER TABLE students ADD COLUMN password_hash VARCHAR(255) NULL')
        cursor.execute('SELECT student_id, password_hash FROM students')
        for student_id, existing_hash in cursor.fetchall():
            if not is_werkzeug_hash(existing_hash):
                initial_password = secrets.token_urlsafe(12)
                cursor.execute(
                    'UPDATE students SET password_hash=%s WHERE student_id=%s',
                    (generate_password_hash(initial_password), student_id),
                )
                generated.append((student_id, initial_password))

        cursor.execute('SELECT COUNT(*) FROM students WHERE password_hash IS NULL OR password_hash NOT LIKE %s AND password_hash NOT LIKE %s', ('scrypt:%', 'pbkdf2:%'))
        if cursor.fetchone()[0]:
            raise RuntimeError('Student password migration left accounts without Werkzeug hashes')
        cursor.execute('ALTER TABLE students MODIFY password_hash VARCHAR(255) NOT NULL')
        if generated:
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with credentials_path.open('x', newline='', encoding='utf-8') as file:
                credentials_file_created = True
                writer = csv.writer(file)
                writer.writerow(['student_id', 'initial_password'])
                writer.writerows(generated)
        connection.commit()
        print(f'Migration complete. Created initial credentials for {len(generated)} students.')
        if generated:
            print(f'Privately distribute then securely delete: {credentials_path}')
    except Exception:
        connection.rollback()
        if credentials_file_created:
            credentials_path.unlink(missing_ok=True)
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--student-credentials', required=True,
        help='new CSV filepath outside the project for initial student passwords',
    )
    args = parser.parse_args()
    migrate(args.student_credentials)
