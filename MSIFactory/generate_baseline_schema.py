#!/usr/bin/env python3
"""
Complete MSIFactory Database Schema Extraction Tool
Generates a comprehensive baseline SQL script from the live database
"""

import sys
import pyodbc
from datetime import datetime
import re

def generate_baseline_schema():
    """Extract complete database schema and generate comprehensive baseline SQL script"""

    print("=" * 60)
    print("MSIFactory Database Schema Extraction Tool")
    print("=" * 60)
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

        # Initialize SQL script
        sql_script = []

        # Header
        sql_script.extend([
            "-- ============================================================",
            "-- MSIFactory Complete Database Baseline Schema Script",
            f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-- Source: Live MSIFactory Database",
            "-- Description: Complete production-ready baseline schema",
            "-- ============================================================",
            "",
            "SET NOCOUNT ON;",
            "SET ANSI_NULLS ON;",
            "SET QUOTED_IDENTIFIER ON;",
            "GO",
            "",
            "-- ============================================================",
            "-- ENVIRONMENT VALIDATION",
            "-- ============================================================",
            "PRINT 'MSIFactory Baseline Schema - Starting Installation...';",
            "PRINT 'Checking SQL Server environment...';",
            "",
            "-- Check SQL Server version",
            "DECLARE @sql_version VARCHAR(50) = @@VERSION;",
            "DECLARE @version_year INT = ",
            "    CASE ",
            "        WHEN @sql_version LIKE '%2019%' THEN 2019",
            "        WHEN @sql_version LIKE '%2017%' THEN 2017",
            "        WHEN @sql_version LIKE '%2016%' THEN 2016",
            "        WHEN @sql_version LIKE '%2014%' THEN 2014",
            "        WHEN @sql_version LIKE '%2012%' THEN 2012",
            "        ELSE 2008",
            "    END;",
            "",
            "IF @version_year < 2012",
            "BEGIN",
            "    PRINT 'ERROR: SQL Server 2012 or later is required.';",
            "    RAISERROR('Unsupported SQL Server version', 16, 1);",
            "    RETURN;",
            "END",
            "",
            "PRINT 'SQL Server version check passed: ' + CAST(@version_year AS VARCHAR(4));",
            "",
            "-- ============================================================",
            "-- DATABASE CREATION",
            "-- ============================================================",
            "IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')",
            "BEGIN",
            "    PRINT 'Creating MSIFactory database...';",
            "    CREATE DATABASE MSIFactory;",
            "    PRINT 'Database MSIFactory created successfully.';",
            "END",
            "ELSE",
            "BEGIN",
            "    PRINT 'Database MSIFactory already exists. Continuing with schema updates...';",
            "END",
            "GO",
            "",
            "USE MSIFactory;",
            "GO",
            "",
            "-- ============================================================",
            "-- DATABASE CONFIGURATION",
            "-- ============================================================",
            "PRINT 'Configuring database settings...';",
            "",
            "-- Set database options for better performance and reliability",
            "ALTER DATABASE MSIFactory SET RECOVERY SIMPLE;",
            "ALTER DATABASE MSIFactory SET AUTO_SHRINK OFF;",
            "ALTER DATABASE MSIFactory SET AUTO_CREATE_STATISTICS ON;",
            "ALTER DATABASE MSIFactory SET AUTO_UPDATE_STATISTICS ON;",
            "ALTER DATABASE MSIFactory SET PAGE_VERIFY CHECKSUM;",
            "",
            "PRINT 'Database configuration completed.';",
            "GO",
            "",
        ])

        # Get all tables
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_SCHEMA = 'dbo'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")

        sql_script.extend([
            "-- ============================================================",
            "-- TABLE CREATION",
            "-- ============================================================",
            "",
            "PRINT 'Creating tables...';",
            "",
        ])

        # Process each table
        for table_name in tables:
            print(f"Processing table: {table_name}")

            sql_script.extend([
                "-- ============================================================",
                f"-- {table_name.upper()} TABLE",
                "-- ============================================================",
                f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')",
                "BEGIN",
                f"    PRINT 'Creating {table_name} table...';",
            ])

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
            sql_script.append(f"    CREATE TABLE {table_name} (")

            column_definitions = []
            for col in columns:
                col_name = col[0]
                data_type = col[1].upper()
                max_length = col[2]
                precision = col[3]
                scale = col[4]
                is_nullable = col[5]
                default_value = col[6]
                is_identity = col[7]

                # Build column definition
                col_def = f"    {col_name} "

                # Data type with proper sizing
                if data_type in ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR']:
                    if max_length == -1:
                        col_def += f"{data_type}(MAX)"
                    else:
                        col_def += f"{data_type}({max_length})"
                elif data_type in ['DECIMAL', 'NUMERIC']:
                    col_def += f"{data_type}({precision},{scale})"
                elif data_type == 'FLOAT':
                    if precision:
                        col_def += f"{data_type}({precision})"
                    else:
                        col_def += data_type
                else:
                    col_def += data_type

                # Identity
                if is_identity:
                    col_def += " IDENTITY(1,1)"

                # Primary key constraint (handled separately)

                # Nullable
                if is_nullable == 'NO':
                    col_def += " NOT NULL"

                # Default value
                if default_value and default_value.strip():
                    col_def += f" DEFAULT {default_value}"

                column_definitions.append(col_def)

            # Add column definitions
            sql_script.extend([col_def + "," if i < len(column_definitions) - 1 else col_def
                              for i, col_def in enumerate(column_definitions)])

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
                sql_script[-1] += ","  # Add comma to last column
                sql_script.append(pk_def)

            sql_script.extend([
                "    );",
                f"    PRINT '{table_name} table created successfully.';",
                "END",
                "ELSE",
                "BEGIN",
                f"    PRINT '{table_name} table already exists.';",
                "END",
                "GO",
                "",
            ])

        # Foreign Keys
        sql_script.extend([
            "-- ============================================================",
            "-- FOREIGN KEY CONSTRAINTS",
            "-- ============================================================",
            "",
            "PRINT 'Creating foreign key constraints...';",
            "",
        ])

        cursor.execute("""
            SELECT
                fk.name AS FK_NAME,
                tp.name AS PARENT_TABLE,
                cp.name AS PARENT_COLUMN,
                tr.name AS REFERENCED_TABLE,
                cr.name AS REFERENCED_COLUMN,
                fk.delete_referential_action_desc,
                fk.update_referential_action_desc
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            ORDER BY tp.name, fk.name
        """)

        foreign_keys = cursor.fetchall()
        print(f"✓ Found {len(foreign_keys)} foreign keys")

        for fk in foreign_keys:
            fk_name = fk[0]
            parent_table = fk[1]
            parent_column = fk[2]
            ref_table = fk[3]
            ref_column = fk[4]
            delete_action = fk[5]
            update_action = fk[6]

            # Build FK constraint
            fk_constraint = f"ALTER TABLE {parent_table} ADD CONSTRAINT {fk_name}\n"
            fk_constraint += f"    FOREIGN KEY ({parent_column}) REFERENCES {ref_table}({ref_column})"

            if delete_action != 'NO_ACTION':
                fk_constraint += f" ON DELETE {delete_action.replace('_', ' ')}"
            if update_action != 'NO_ACTION':
                fk_constraint += f" ON UPDATE {update_action.replace('_', ' ')}"

            sql_script.extend([
                f"-- Foreign key: {parent_table}.{parent_column} -> {ref_table}.{ref_column}",
                f"IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = '{fk_name}')",
                f"    {fk_constraint};",
                "",
            ])

        # Check Constraints
        sql_script.extend([
            "-- ============================================================",
            "-- CHECK CONSTRAINTS",
            "-- ============================================================",
            "",
            "PRINT 'Creating check constraints...';",
            "",
        ])

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
        print(f"✓ Found {len(check_constraints)} check constraints")

        for check in check_constraints:
            constraint_name = check[0]
            check_clause = check[1]
            table_name = check[2]

            sql_script.extend([
                f"-- Check constraint for {table_name}",
                f"IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = '{constraint_name}')",
                f"    ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name}",
                f"        CHECK {check_clause};",
                "",
            ])

        # Indexes
        sql_script.extend([
            "-- ============================================================",
            "-- INDEXES FOR PERFORMANCE",
            "-- ============================================================",
            "",
            "PRINT 'Creating indexes...';",
            "",
        ])

        cursor.execute("""
            SELECT
                i.name AS INDEX_NAME,
                t.name AS TABLE_NAME,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS COLUMNS,
                i.is_unique,
                i.type_desc
            FROM sys.indexes i
            INNER JOIN sys.tables t ON i.object_id = t.object_id
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.type > 0 AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
            GROUP BY i.name, t.name, i.is_unique, i.type_desc
            ORDER BY t.name, i.name
        """)

        indexes = cursor.fetchall()
        print(f"✓ Found {len(indexes)} indexes")

        for idx in indexes:
            index_name = idx[0]
            table_name = idx[1]
            columns = idx[2]
            is_unique = idx[3]
            index_type = idx[4]

            unique_clause = "UNIQUE " if is_unique else ""
            sql_script.extend([
                f"-- Index on {table_name}({columns})",
                f"IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = '{index_name}' AND object_id = OBJECT_ID('{table_name}'))",
                f"    CREATE {unique_clause}INDEX {index_name} ON {table_name}({columns});",
                "",
            ])

        # Sample Data for key tables
        sql_script.extend([
            "-- ============================================================",
            "-- SAMPLE DATA",
            "-- ============================================================",
            "",
            "PRINT 'Inserting sample data...';",
            "",
        ])

        # Users table sample data
        if 'users' in tables:
            cursor.execute("""
                SELECT username, email, first_name, last_name, status, role, created_date, is_active
                FROM users
                WHERE username IN ('admin', 'john.doe')
                ORDER BY username
            """)

            sample_users = cursor.fetchall()
            if sample_users:
                sql_script.extend([
                    "-- Insert sample users",
                    "IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')",
                ])

                for user in sample_users:
                    username, email, first_name, last_name, status, role, created_date, is_active = user
                    sql_script.append(
                        f"INSERT INTO users (username, email, first_name, last_name, status, role, created_date, is_active) "
                        f"VALUES ('{username}', '{email}', '{first_name}', '{last_name}', '{status}', '{role}', GETDATE(), {1 if is_active else 0});"
                    )

                sql_script.append("")

        # Finalize script
        sql_script.extend([
            "-- ============================================================",
            "-- FINAL VALIDATION AND CLEANUP",
            "-- ============================================================",
            "",
            "PRINT 'Running final validation...';",
            "",
            "-- Update statistics for better performance",
            "UPDATE STATISTICS users;",
            "UPDATE STATISTICS projects;",
            "",
            "-- ============================================================",
            "-- INSTALLATION SUMMARY",
            "-- ============================================================",
            "PRINT '============================================================';",
            "PRINT 'MSIFactory Database Schema Installation COMPLETED';",
            "PRINT '============================================================';",
            f"PRINT 'Total Tables: {len(tables)}';",
            f"PRINT 'Total Foreign Keys: {len(foreign_keys)}';",
            f"PRINT 'Total Check Constraints: {len(check_constraints)}';",
            f"PRINT 'Total Indexes: {len(indexes)}';",
            "PRINT 'Installation Date: ' + CONVERT(VARCHAR, GETDATE(), 120);",
            "PRINT '';",
            "PRINT 'Database is ready for use!';",
            "PRINT '============================================================';",
            "",
            "GO",
            "SET NOCOUNT OFF;",
        ])

        # Write to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_filename = f"baselineSQLScript_{timestamp}.sql"
        script_content = '\n'.join(sql_script)

        with open(script_filename, 'w', encoding='utf-8') as f:
            f.write(script_content)

        conn.close()

        print("\n" + "=" * 60)
        print("SCHEMA EXTRACTION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"✓ Generated file: {script_filename}")
        print(f"✓ Total tables: {len(tables)}")
        print(f"✓ Total foreign keys: {len(foreign_keys)}")
        print(f"✓ Total check constraints: {len(check_constraints)}")
        print(f"✓ Total indexes: {len(indexes)}")
        print(f"✓ Script size: {len(script_content):,} characters")
        print("\nThe baseline SQL script is ready for deployment to fresh database instances.")

        return script_filename

    except Exception as e:
        print(f"❌ Error extracting schema: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_baseline_schema()