#!/usr/bin/env python3
"""
Check user_projects table structure and constraints
"""

import sys
sys.path.append('.')

def check_table_structure():
    """Check the actual structure of user_projects table"""
    print("=== Checking user_projects table structure ===")

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        with pyodbc.connect(conn_str, timeout=5) as conn:
            with conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_NAME = 'user_projects'
                """)

                if not cursor.fetchone():
                    print("ERROR: user_projects table does not exist!")
                    return

                # Get table structure
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = 'user_projects'
                    ORDER BY ORDINAL_POSITION
                """)

                print("\n=== Table Structure ===")
                columns = cursor.fetchall()
                for row in columns:
                    print(f"  {row[0]}: {row[1]} (Nullable: {row[2]}, Default: {row[3]})")

                # Check constraints
                cursor.execute("""
                    SELECT
                        tc.CONSTRAINT_NAME,
                        tc.CONSTRAINT_TYPE,
                        cc.CHECK_CLAUSE
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
                        ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
                    WHERE tc.TABLE_NAME = 'user_projects'
                """)

                print("\n=== Constraints ===")
                constraints = cursor.fetchall()
                for row in constraints:
                    print(f"  {row[0]}: {row[1]} - {row[2]}")

                # Try to see what values are currently in access_level column
                cursor.execute("""
                    SELECT DISTINCT access_level, COUNT(*) as count
                    FROM user_projects
                    GROUP BY access_level
                """)

                print("\n=== Current access_level values in table ===")
                try:
                    access_levels = cursor.fetchall()
                    if access_levels:
                        for row in access_levels:
                            print(f"  '{row[0]}': {row[1]} records")
                    else:
                        print("  No records found in user_projects table")
                except Exception as e:
                    print(f"  Error reading existing values: {e}")

                # Test insert with different values
                print("\n=== Testing INSERT with different access_level values ===")
                test_values = ['read', 'write', 'admin', 'user', 'view', 'member']

                for test_value in test_values:
                    try:
                        # Try a test insert (we'll rollback)
                        cursor.execute("BEGIN TRANSACTION")
                        cursor.execute("""
                            INSERT INTO user_projects (user_id, project_id, access_level)
                            VALUES (999999, 999999, ?)
                        """, (test_value,))
                        cursor.execute("ROLLBACK")
                        print(f"  ✓ '{test_value}' - VALID")
                    except Exception as e:
                        cursor.execute("ROLLBACK")
                        print(f"  ✗ '{test_value}' - INVALID: {str(e)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table_structure()