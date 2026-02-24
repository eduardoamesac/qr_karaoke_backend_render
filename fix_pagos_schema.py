#!/usr/bin/env python3
"""Fix pagos table schema - remove unused columns."""

from database import SessionLocal, engine
from sqlalchemy import text

def fix_pagos_table():
    """Remove cuenta_id column from pagos table if it exists."""
    with engine.connect() as conn:
        # First, drop the foreign key constraint if it exists
        try:
            print("Removing foreign key constraint pagos_ibfk_2...")
            conn.execute(text("ALTER TABLE pagos DROP FOREIGN KEY pagos_ibfk_2"))
            conn.commit()
            print("✓ Foreign key removed")
        except Exception as e:
            if "1091" not in str(e):  # Error 1091 = constraint doesn't exist
                print(f"Note: {e}")
        
        # Check if cuenta_id column exists
        result = conn.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='pagos' AND COLUMN_NAME='cuenta_id'
        """))
        
        has_cuenta_id = result.fetchone() is not None
        
        if has_cuenta_id:
            print("Removing cuenta_id column from pagos table...")
            conn.execute(text("ALTER TABLE pagos DROP COLUMN cuenta_id"))
            conn.commit()
            print("✓ Column removed successfully")
        else:
            print("✓ Column cuenta_id does not exist (already clean)")
        
        # Verify final structure
        result = conn.execute(text("""
            SELECT COLUMN_NAME, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='pagos'
            ORDER BY ORDINAL_POSITION
        """))
        
        print("\nFinal pagos table structure:")
        for row in result:
            print(f"  - {row[0]}: {row[1]}")

if __name__ == "__main__":
    try:
        fix_pagos_table()
        print("\n✓ Database schema fixed successfully!")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
