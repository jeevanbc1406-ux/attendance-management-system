"""Add explicit faculty login-to-record links to one explicitly selected DB."""

import argparse
import os

import MySQLdb
from dotenv import load_dotenv


def migrate(database):
    load_dotenv('.env')
    configured_database = os.environ.get('MYSQL_DB', 'attendance_db')
    if database != configured_database:
        raise RuntimeError('--database must match MYSQL_DB in .env')

    connection = MySQLdb.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ['MYSQL_USER'],
        passwd=os.environ['MYSQL_PASSWORD'],
        db=database,
        port=int(os.environ.get('MYSQL_PORT', '3307')),
        charset='utf8mb4',
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users' AND COLUMN_NAME='faculty_id'""",
            (database,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute('ALTER TABLE users ADD COLUMN faculty_id INT NULL')

        cursor.execute(
            """SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
               WHERE CONSTRAINT_SCHEMA=%s AND TABLE_NAME='users'
                 AND CONSTRAINT_NAME='users_faculty_id_uk'""",
            (database,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute('ALTER TABLE users ADD CONSTRAINT users_faculty_id_uk UNIQUE (faculty_id)')

        cursor.execute(
            """SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
               WHERE CONSTRAINT_SCHEMA=%s AND TABLE_NAME='users'
                 AND CONSTRAINT_NAME='users_faculty_id_fk'""",
            (database,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'ALTER TABLE users ADD CONSTRAINT users_faculty_id_fk '
                'FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)'
            )

        # The demo's sole faculty login is the seeded teacher account for
        # faculty record 1. Do not guess links for any other faculty users.
        cursor.execute(
            """UPDATE users
               SET faculty_id=(SELECT faculty_id FROM faculty ORDER BY faculty_id LIMIT 1)
               WHERE username='teacher' AND role='faculty' AND faculty_id IS NULL
                 AND EXISTS (SELECT 1 FROM faculty)"""
        )
        cursor.execute("SELECT username FROM users WHERE role='faculty' AND faculty_id IS NULL")
        unlinked = [row[0] for row in cursor.fetchall()]
        if unlinked:
            raise RuntimeError('Faculty logins need explicit faculty_id links: ' + ', '.join(unlinked))
        connection.commit()
        print(f'Faculty login links are installed in {database}.')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Must match MYSQL_DB in .env')
    migrate(parser.parse_args().database)
