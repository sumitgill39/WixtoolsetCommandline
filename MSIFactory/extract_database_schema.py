#!/usr/bin/env python3
"""
Extract complete database schema from MSIFactory database
"""

import sys
import pyodbc
from datetime import datetime

def extract_database_schema():
    """Extract complete database schema and generate baseline SQL script"""

    print("=== MSIFactory Database Schema Extraction ===")
    print(f"Started at: {datetime.now()}")

    try:
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        print("✓ Connected to MSIFactory database")

        # Start building the SQL script
        sql_script = []
        sql_script.append("-- ============================================================")
        sql_script.append("-- MSIFactory Database Baseline Schema Script")
        sql_script.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_script.append("-- Source: Live MSIFactory Database")
        sql_script.append("-- ============================================================")
        sql_script.append("")
        sql_script.append("SET NOCOUNT ON;")
        sql_script.append("GO")
        sql_script.append("")

        # Database creation
        sql_script.append("-- ============================================================")
        sql_script.append("-- DATABASE CREATION")
        sql_script.append("-- ============================================================")
        sql_script.append("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')")
        sql_script.append("BEGIN")
        sql_script.append("    PRINT 'Creating MSIFactory database...';")
        sql_script.append("    CREATE DATABASE MSIFactory;")
        sql_script.append("    PRINT 'Database MSIFactory created successfully.';")
        sql_script.append("END")
        sql_script.append("ELSE")
        sql_script.append("BEGIN")
        sql_script.append("    PRINT 'Database MSIFactory already exists. Continuing with schema updates...';")
        sql_script.append("END")
        sql_script.append("GO")
        sql_script.append("")
        sql_script.append("USE MSIFactory;")
        sql_script.append("GO")
        sql_script.append("")

        # Get all user tables
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_SCHEMA = 'dbo'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")

        sql_script.append("-- ============================================================")
        sql_script.append("-- TABLE CREATION")
        sql_script.append("-- ============================================================")
        sql_script.append("")

        # Process each table
        for table_name in tables:
            print(f"Processing table: {table_name}")

            sql_script.append(f"-- ============================================================")
            sql_script.append(f"-- {table_name.upper()} TABLE")
            sql_script.append(f"-- ============================================================")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')")
            sql_script.append("BEGIN")
            sql_script.append(f"    PRINT 'Creating {table_name} table...';")

            # Get table structure
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

            # Build CREATE TABLE statement
            create_table = f"    CREATE TABLE {table_name} ("
            sql_script.append(create_table)

            column_definitions = []
            for col in columns:
                col_name = col[0]
                data_type = col[1]
                max_length = col[2]
                precision = col[3]
                scale = col[4]
                is_nullable = col[5]
                default_value = col[6]
                is_identity = col[7]

                # Build column definition
                col_def = f"    {col_name} "

                # Data type
                if data_type.upper() in ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR']:
                    if max_length == -1:
                        col_def += f"{data_type.upper()}(MAX)"
                    else:
                        col_def += f"{data_type.upper()}({max_length})"
                elif data_type.upper() in ['DECIMAL', 'NUMERIC']:
                    col_def += f"{data_type.upper()}({precision},{scale})"
                else:
                    col_def += data_type.upper()

                # Identity
                if is_identity:
                    col_def += " IDENTITY(1,1)"

                # Primary key (we'll handle this separately)

                # Nullable
                if is_nullable == 'NO':
                    col_def += " NOT NULL"

                # Default value
                if default_value:
                    col_def += f" DEFAULT {default_value}"

                column_definitions.append(col_def)

            # Add column definitions
            for i, col_def in enumerate(column_definitions):
                if i < len(column_definitions) - 1:
                    sql_script.append(col_def + ",")
                else:
                    sql_script.append(col_def)

            # Get primary key
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_NAME = ? AND CONSTRAINT_NAME LIKE 'PK_%'
                ORDER BY ORDINAL_POSITION
            """, table_name)

            pk_columns = [row[0] for row in cursor.fetchall()]
            if pk_columns:
                pk_def = f"    CONSTRAINT PK_{table_name} PRIMARY KEY ({', '.join(pk_columns)})"
                sql_script.append(f",")
                sql_script.append(pk_def)

            sql_script.append("    );")
            sql_script.append(f"    PRINT '{table_name} table created successfully.';")
            sql_script.append("END")
            sql_script.append("ELSE")
            sql_script.append("BEGIN")
            sql_script.append(f"    PRINT '{table_name} table already exists.';")
            sql_script.append("END")
            sql_script.append("GO")
            sql_script.append("")

        # Get all foreign keys
        sql_script.append("-- ============================================================")
        sql_script.append("-- FOREIGN KEY CONSTRAINTS")
        sql_script.append("-- ============================================================")

        cursor.execute("""
            SELECT
                fk.name AS FK_NAME,
                tp.name AS PARENT_TABLE,
                cp.name AS PARENT_COLUMN,
                tr.name AS REFERENCED_TABLE,
                cr.name AS REFERENCED_COLUMN
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            ORDER BY tp.name, fk.name
        """)

        foreign_keys = cursor.fetchall()

        for fk in foreign_keys:
            fk_name = fk[0]
            parent_table = fk[1]
            parent_column = fk[2]
            ref_table = fk[3]
            ref_column = fk[4]

            sql_script.append(f"-- Add foreign key: {parent_table}.{parent_column} -> {ref_table}.{ref_column}")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = '{fk_name}')")
            sql_script.append(f"    ALTER TABLE {parent_table} ADD CONSTRAINT {fk_name}")
            sql_script.append(f"        FOREIGN KEY ({parent_column}) REFERENCES {ref_table}({ref_column});")
            sql_script.append("")

        # Get all check constraints
        sql_script.append("-- ============================================================")
        sql_script.append("-- CHECK CONSTRAINTS")
        sql_script.append("-- ============================================================")

        cursor.execute("""
            SELECT
                cc.CONSTRAINT_NAME,
                cc.CHECK_CLAUSE,
                tc.TABLE_NAME
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
            INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            ORDER BY tc.TABLE_NAME, cc.CONSTRAINT_NAME
        """)

        check_constraints = cursor.fetchall()

        for check in check_constraints:
            constraint_name = check[0]
            check_clause = check[1]
            table_name = check[2]

            sql_script.append(f"-- Add check constraint to {table_name}")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = '{constraint_name}')")
            sql_script.append(f"    ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name}")
            sql_script.append(f"        CHECK {check_clause};")
            sql_script.append("")

        # Get all indexes
        sql_script.append("-- ============================================================")
        sql_script.append("-- INDEXES")
        sql_script.append("-- ============================================================")

        cursor.execute("""
            SELECT
                i.name AS INDEX_NAME,
                t.name AS TABLE_NAME,
                STRING_AGG(c.name, ', ') AS COLUMNS,
                i.is_unique
            FROM sys.indexes i
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.type > 0 AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
            GROUP BY i.name, t.name, i.is_unique
            ORDER BY t.name, i.name
        """)

        indexes = cursor.fetchall()

        for idx in indexes:
            index_name = idx[0]
            table_name = idx[1]
            columns = idx[2]
            is_unique = idx[3]

            unique_clause = "UNIQUE " if is_unique else ""
            sql_script.append(f"-- Create index on {table_name}")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = '{index_name}')")
            sql_script.append(f"    CREATE {unique_clause}INDEX {index_name} ON {table_name}({columns});")
            sql_script.append("")

        # Get sample data from key tables
        sql_script.append("-- ============================================================")
        sql_script.append("-- SAMPLE DATA")
        sql_script.append("-- ============================================================")

        # Sample data for users table
        if 'users' in tables:
            cursor.execute("SELECT TOP 5 * FROM users")
            sample_users = cursor.fetchall()
            if sample_users:
                sql_script.append("-- Insert sample users")
                for user in sample_users:
                    # Build INSERT statement (simplified)
                    sql_script.append(f"-- Sample user data would go here")

        # Finalize script
        sql_script.append("-- ============================================================")
        sql_script.append("-- SCRIPT COMPLETION")
        sql_script.append("-- ============================================================")
        sql_script.append("PRINT 'MSIFactory Database Schema Installation Complete';")
        sql_script.append("PRINT 'Total Tables Created: " + str(len(tables)) + "';")
        sql_script.append("GO")
        sql_script.append("SET NOCOUNT OFF;")

        # Write to file
        script_content = '\n'.join(sql_script)

        with open('baselineSQLScript.sql', 'w', encoding='utf-8') as f:
            f.write(script_content)

        print(f"✓ Schema extraction completed")
        print(f"✓ Generated baselineSQLScript.sql with {len(tables)} tables")
        print(f"✓ Script includes: Tables, Primary Keys, Foreign Keys, Check Constraints, Indexes")

        conn.close()

        return script_content

    except Exception as e:
        print(f"❌ Error extracting schema: {e}")
        return None

if __name__ == "__main__":
    extract_database_schema()