"""
csv_to_sql.py

Load one or more CSV files into a SQLite database, with automatic
schema inference from the CSV headers and data types.

Usage:
    python3 csv_to_sql.py --csv cpc_database.csv --table cpc_centers --db clinics.db
    python3 csv_to_sql.py --csv cpc_database.csv pp_health+centers_with_address.csv --table cpcs pps --db clinics.db

If you only pass one --csv, --table defaults to the CSV filename (no extension).
"""

import argparse
import sqlite3
import pandas as pd
from pathlib import Path


def infer_sqlite_dtype(series: pd.Series) -> str:
    """Map a pandas dtype to a reasonable SQLite column type."""
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    if pd.api.types.is_bool_dtype(series):
        return "INTEGER"  # SQLite has no native BOOLEAN
    return "TEXT"


def load_csv_to_sqlite(csv_path: str, table_name: str, db_path: str, if_exists: str = "replace"):
    """
    Read a CSV and write it into a SQLite database as a table.

    if_exists: 'replace', 'append', or 'fail' (passed straight to pandas.to_sql)
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Read everything as string first to avoid pandas guessing wrong on
    # things like zip codes (which should stay text, not become floats/ints).
    df = pd.read_csv(path, dtype=str)

    # Optional: try to convert numeric-looking columns EXCEPT known
    # id/code fields that should always stay text (zip codes, tax IDs, etc.)
    preserve_as_text = {"zip", "zip_code", "tax_id", "postal_code"}
    for col in df.columns:
        if col.lower() in preserve_as_text:
            continue
        try:
            converted = pd.to_numeric(df[col])
            df[col] = converted
        except (ValueError, TypeError):
            pass  # leave as text if conversion fails

    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)

        # Report the resulting schema so you can see what was inferred
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        print(f"\nTable '{table_name}' created in {db_path} with {len(df)} rows.")
        print("Schema:")
        for col_info in cursor.fetchall():
            # col_info: (cid, name, type, notnull, dflt_value, pk)
            print(f"  {col_info[1]:<25} {col_info[2]}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load CSV file(s) into a SQLite database.")
    parser.add_argument("--csv", nargs="+", required=True, help="Path(s) to CSV file(s)")
    parser.add_argument("--table", nargs="+", help="Table name(s), matching order of --csv. Defaults to CSV filename.")
    parser.add_argument("--db", default="data.db", help="Path to SQLite database file (created if it doesn't exist)")
    parser.add_argument("--if-exists", default="replace", choices=["replace", "append", "fail"],
                         help="Behavior if table already exists (default: replace)")
    args = parser.parse_args()

    csv_paths = args.csv
    table_names = args.table if args.table else [Path(p).stem for p in csv_paths]

    if len(table_names) != len(csv_paths):
        raise ValueError("Number of --table names must match number of --csv files")

    for csv_path, table_name in zip(csv_paths, table_names):
        load_csv_to_sqlite(csv_path, table_name, args.db, args.if_exists)

    print(f"\nDone. Query it with: sqlite3 {args.db}")


if __name__ == "__main__":
    main()