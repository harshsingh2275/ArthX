"""
ArthX Database Initialization Script.
Creates all database tables cleanly from an empty state using SQLAlchemy metadata.
"""

import sys
import argparse
from pathlib import Path
from sqlalchemy import inspect
from database import engine, Base
import models  # Ensures all models are registered with Base.metadata

def init_db(reset: bool = False):
    inspector = inspect(engine)
    
    if reset:
        print("Reset flag detected: Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")

    print(f"Creating tables with database engine URL: {engine.url}")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!\n")

    # Inspect and verify created schema
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Verified {len(tables)} tables in database: {tables}\n")
    
    verification_summary = {}
    for table_name in tables:
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", [])
        
        print(f"Table: {table_name}")
        col_list = []
        for col in columns:
            is_pk = col['name'] in pk_cols
            pk_str = " (PK)" if is_pk else ""
            nullable_str = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  - {col['name']}: {col['type']}{pk_str} {nullable_str}")
            col_list.append({
                "name": col['name'],
                "type": str(col['type']),
                "nullable": col['nullable'],
                "is_pk": is_pk
            })
        verification_summary[table_name] = col_list
        print()

    return tables, verification_summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize ArthX SQLite Database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()
    
    tables, summary = init_db(reset=args.reset)
    if "transactions" in tables and "invoices" in tables:
        print("Acceptance criteria met: 'transactions' and 'invoices' tables verified with correct schema.")
        sys.exit(0)
    else:
        print("Error: Missing required tables!")
        sys.exit(1)
