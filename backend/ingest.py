"""
ArthX CLI Ingestion Script — T1.2
Run directly to seed the database without starting the FastAPI server.
Usage: python ingest.py [--dry-run]

Idempotent: running this multiple times always produces the same row count.
"""

import sys
import argparse
from database import SessionLocal, engine, Base
import models  # registers all models with Base

from services.ingestion import run_ingestion

def main():
    parser = argparse.ArgumentParser(description="ArthX seed data ingestion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse CSVs and report counts without writing to DB")
    args = parser.parse_args()

    # Ensure tables exist before trying to write
    Base.metadata.create_all(bind=engine)

    if args.dry_run:
        print("DRY RUN — no data will be written to the database.")
        from pathlib import Path
        import csv
        from config import ROOT_DIR
        data_dir = ROOT_DIR / "data"
        for fname in ["transactions.csv", "invoices.csv"]:
            p = data_dir / fname
            if p.exists():
                with open(p, newline="", encoding="utf-8") as f:
                    row_count = sum(1 for _ in csv.DictReader(f))
                print(f"  {fname}: {row_count} rows (would be loaded)")
            else:
                print(f"  {fname}: NOT FOUND at {p}")
        return

    db = SessionLocal()
    try:
        print("Starting ArthX seed data ingestion...")
        result = run_ingestion(db)

        print(f"\nStatus   : {result['status']}")
        print(f"Cleared  : {result['cleared']}")
        print(f"Loaded   : {result['loaded']}")
        print(f"\n{result['message']}")

        # Final verification — query back the actual counts
        from models.transaction import Transaction
        from models.invoice import Invoice
        tx_count = db.query(Transaction).count()
        inv_count = db.query(Invoice).count()
        print(f"\nVerification (live query):")
        print(f"  transactions table: {tx_count} rows")
        print(f"  invoices table    : {inv_count} rows")

        if tx_count != result["loaded"]["transactions"]:
            print("ERROR: transaction count mismatch — ingestion may be incomplete!")
            sys.exit(1)
        if inv_count != result["loaded"]["invoices"]:
            print("ERROR: invoice count mismatch — ingestion may be incomplete!")
            sys.exit(1)

        print("\nIngestion complete. Run again to verify idempotency.")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
