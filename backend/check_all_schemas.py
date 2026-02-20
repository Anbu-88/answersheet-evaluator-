from db.session import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = ["users", "classes", "subjects", "class_subject_teacher", "tests", "submissions", "disputes"]

for table in tables:
    print(f"--- Table: {table} ---")
    try:
        columns = inspector.get_columns(table)
        for column in columns:
            print(f"Column: {column['name']}, Type: {column['type']}")
    except Exception as e:
        print(f"Error checking table {table}: {e}")
