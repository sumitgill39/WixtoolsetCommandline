#!/usr/bin/env python3
"""
Simple MSIFactory Database Schema Extractor
Generates baselineSQLScript.sql from live database
"""

import sys
import os

# Add current directory to path for imports
sys.path.append('.')

def create_baseline_sql():
    """Generate baseline SQL script from MSIFactory database"""

    try:
        import pyodbc
        from datetime import datetime

        print("Connecting to MSIFactory database...")

        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        print("✓ Connected successfully")

        # Start building SQL script
        sql_lines = []

        # Header
        sql_lines.extend([
            "-- ============================================================",
            "-- MSIFactory Database Baseline Schema Script",
            f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-- Source: Live MSIFactory Database",
            "-- ============================================================",
            "",
            "SET NOCOUNT ON;",
            "GO",
            "",
            "-- Database Creation",
            "IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')",
            "BEGIN",
            "    CREATE DATABASE MSIFactory;",
            "    PRINT 'MSIFactory database created';",
            "END",
            "GO",
            "",
            "USE MSIFactory;",
            "GO",
            "",
        ])

        # Get all tables
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(tables)} tables: {', '.join(tables)}")

        # Process each table
        for table_name in tables:
            print(f"Processing: {table_name}")

            sql_lines.extend([
                f"-- {table_name} Table",
                f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')",
                "BEGIN",
            ])

            # Get columns
            cursor.execute("""
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, table_name)

            columns = cursor.fetchall()
            sql_lines.append(f"    CREATE TABLE {table_name} (")

            # Build column definitions
            col_defs = []
            for col in columns:
                col_name, data_type, max_len, precision, scale, nullable, default, is_identity = col

                # Build column definition
                col_def = f"        {col_name} "

                # Data type
                if data_type.upper() in ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR']:
                    if max_len == -1:
                        col_def += f"{data_type.upper()}(MAX)"
                    else:
                        col_def += f"{data_type.upper()}({max_len})"
                elif data_type.upper() in ['DECIMAL', 'NUMERIC']:
                    col_def += f"{data_type.upper()}({precision},{scale})"
                else:
                    col_def += data_type.upper()

                # Identity
                if is_identity:
                    col_def += " IDENTITY(1,1)"

                # Nullable
                if nullable == 'NO':
                    col_def += " NOT NULL"

                # Default
                if default and str(default).strip() and str(default) != 'NULL':
                    col_def += f" DEFAULT {default}"

                col_defs.append(col_def)

            # Add columns
            for i, col_def in enumerate(col_defs):
                if i < len(col_defs) - 1:
                    sql_lines.append(col_def + ",")
                else:
                    sql_lines.append(col_def)

            # Primary key
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_NAME = ? AND CONSTRAINT_NAME LIKE 'PK_%'
                ORDER BY ORDINAL_POSITION
            """, table_name)

            pk_cols = [row[0] for row in cursor.fetchall()]
            if pk_cols:
                sql_lines[-1] += ","
                sql_lines.append(f"        CONSTRAINT PK_{table_name} PRIMARY KEY ({', '.join(pk_cols)})")

            sql_lines.extend([
                "    );",
                "END",
                "GO",
                "",
            ])

        # Foreign keys
        sql_lines.append("-- Foreign Key Constraints")
        cursor.execute("""
            SELECT
                fk.name,
                tp.name,
                cp.name,
                tr.name,
                cr.name
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            ORDER BY tp.name
        """)

        fks = cursor.fetchall()
        for fk_name, parent_table, parent_col, ref_table, ref_col in fks:
            sql_lines.extend([
                f"IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = '{fk_name}')",
                f"    ALTER TABLE {parent_table} ADD CONSTRAINT {fk_name}",
                f"        FOREIGN KEY ({parent_col}) REFERENCES {ref_table}({ref_col});",
                "",
            ])

        # Check constraints
        sql_lines.append("-- Check Constraints")
        cursor.execute("""
            SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE, tc.TABLE_NAME
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
            INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            ORDER BY tc.TABLE_NAME
        """)

        checks = cursor.fetchall()
        for constraint_name, check_clause, table_name in checks:
            sql_lines.extend([
                f"IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = '{constraint_name}')",
                f"    ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name}",
                f"        CHECK {check_clause};",
                "",
            ])

        # Footer
        sql_lines.extend([
            "-- Script Complete",
            f"PRINT 'MSIFactory schema created - {len(tables)} tables, {len(fks)} foreign keys, {len(checks)} check constraints';",
            "GO",
            "SET NOCOUNT OFF;",
        ])

        # Write to file
        script_content = '\n'.join(sql_lines)
        filename = "baselineSQLScript.sql"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(script_content)

        conn.close()

        print(f"\n✓ Successfully created {filename}")
        print(f"✓ Tables: {len(tables)}")
        print(f"✓ Foreign Keys: {len(fks)}")
        print(f"✓ Check Constraints: {len(checks)}")
        print(f"✓ File size: {len(script_content):,} characters")
        print(f"\nBaseline SQL script is ready for deployment!")

        return filename

    except ImportError:
        print("❌ Error: pyodbc module not found")
        print("Please install: pip install pyodbc")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    create_baseline_sql()