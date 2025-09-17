#!/usr/bin/env python3
"""
Diagnose database schema to understand table relationships
"""

import sys
sys.path.append('.')

def diagnose_database():
    """Check what tables exist and their foreign key relationships"""
    print("=== Database Schema Diagnosis ===")

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
                # Get all tables
                cursor.execute("""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """)
                tables = [row[0] for row in cursor.fetchall()]

                print(f"Available tables: {tables}")

                # Check msi_configurations structure
                if 'msi_configurations' in tables:
                    print(f"\n=== msi_configurations table structure ===")
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME = 'msi_configurations'
                        ORDER BY ORDINAL_POSITION
                    """)
                    for row in cursor.fetchall():
                        print(f"  {row[0]} ({row[1]}) - Nullable: {row[2]}")

                    # Check foreign key constraints
                    cursor.execute("""
                        SELECT
                            fk.name AS FK_Name,
                            tp.name AS Parent_Table,
                            cp.name AS Parent_Column,
                            tr.name AS Referenced_Table,
                            cr.name AS Referenced_Column
                        FROM sys.foreign_keys fk
                        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                        INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
                        INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
                        INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
                        INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
                        WHERE tp.name = 'msi_configurations'
                    """)

                    print(f"\n=== Foreign keys from msi_configurations ===")
                    fk_found = False
                    for row in cursor.fetchall():
                        fk_found = True
                        print(f"  FK: {row[0]} - {row[1]}.{row[2]} -> {row[3]}.{row[4]}")

                    if not fk_found:
                        print("  No foreign keys found")

                # Check what records exist for project 10
                if 'msi_configurations' in tables:
                    cursor.execute("SELECT COUNT(*) FROM msi_configurations WHERE component_id = ?", (10,))
                    component_count = cursor.fetchone()[0]
                    print(f"\n=== Records for project/component 10 ===")
                    print(f"msi_configurations with component_id=10: {component_count}")

                    try:
                        cursor.execute("SELECT COUNT(*) FROM msi_configurations WHERE project_id = ?", (10,))
                        project_count = cursor.fetchone()[0]
                        print(f"msi_configurations with project_id=10: {project_count}")
                    except Exception as e:
                        print(f"No project_id column in msi_configurations: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose_database()