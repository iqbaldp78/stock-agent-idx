import os
from sqlalchemy import create_engine, inspect
from db.models import Base
from db import clean_db_url

engine = create_engine(clean_db_url)
inspector = inspect(engine)

print("=== CHECKING MISSING TABLES ===")
for table_name, table in Base.metadata.tables.items():
    if not inspector.has_table(table_name):
        print(f"MISSING TABLE: {table_name}")
    else:
        existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
        model_cols = {col.name for col in table.columns}
        missing_cols = model_cols - existing_cols
        if missing_cols:
            print(f"TABLE {table_name} MISSING COLUMNS: {sorted(missing_cols)}")

print("=== DONE ===")
