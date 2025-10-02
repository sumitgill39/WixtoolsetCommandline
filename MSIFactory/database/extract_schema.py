"""
MSIFactory Schema Extractor v7.0
Connects to SQL Server and extracts complete database schema
"""

import pyodbc
import sys
from datetime import datetime

# Connection parameters from config
DB_SERVER = "SUMEETGILL7E47\\MSSQLSERVER01"
DB_NAME = "MSIFactory"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_TRUST_CONNECTION = "yes"
DB_PORT = "1433"

# Connection string options to try
connection_strings = [
    f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
    f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER},{DB_PORT};DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
    f"DRIVER={{SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
    f"DRIVER={{{DB_DRIVER}}};SERVER=localhost\\MSSQLSERVER01;DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
    f"DRIVER={{{DB_DRIVER}}};SERVER=.\\MSSQLSERVER01;DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
    f"DRIVER={{SQL Server Native Client 11.0}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection={DB_TRUST_CONNECTION};",
]

def connect_to_database():
    """Try multiple connection strings to connect to SQL Server"""
    for i, conn_str in enumerate(connection_strings, 1):
        try:
            print(f"Attempt {i}: Trying connection string...")
            conn = pyodbc.connect(conn_str, timeout=10)
            print(f"[OK] Successfully connected using method {i}")
            return conn
        except Exception as e:
            print(f"[FAIL] Failed: {str(e)[:100]}")

    print("\n[ERROR] All connection attempts failed!")
    print("\nPlease verify:")
    print("1. SQL Server instance 'MSSQLSERVER01' is running")
    print("2. SQL Server Browser service is running")
    print("3. TCP/IP protocol is enabled in SQL Server Configuration Manager")
    print("4. Named Pipes is enabled")
    sys.exit(1)

def get_all_tables(cursor):
    """Retrieve all user tables"""
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        AND TABLE_SCHEMA = 'dbo'
        ORDER BY TABLE_NAME
    """)
    return [row[0] for row in cursor.fetchall()]

def get_table_schema(cursor, table_name):
    """Get complete schema for a table including columns, types, constraints"""
    cursor.execute(f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            NUMERIC_SCALE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA + '.' + TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
    """)
    return cursor.fetchall()

def get_primary_keys(cursor, table_name):
    """Get primary key constraints"""
    cursor.execute(f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = '{table_name}'
        AND CONSTRAINT_NAME LIKE 'PK%'
        ORDER BY ORDINAL_POSITION
    """)
    return [row[0] for row in cursor.fetchall()]

def get_foreign_keys(cursor, table_name):
    """Get foreign key constraints"""
    cursor.execute(f"""
        SELECT
            fk.name AS FK_NAME,
            OBJECT_NAME(fkc.parent_object_id) AS TABLE_NAME,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS COLUMN_NAME,
            OBJECT_NAME(fkc.referenced_object_id) AS REFERENCED_TABLE,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS REFERENCED_COLUMN,
            fk.delete_referential_action_desc,
            fk.update_referential_action_desc
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        WHERE OBJECT_NAME(fkc.parent_object_id) = '{table_name}'
    """)
    return cursor.fetchall()

def get_indexes(cursor, table_name):
    """Get indexes for a table"""
    cursor.execute(f"""
        SELECT
            i.name AS INDEX_NAME,
            i.is_unique,
            COL_NAME(ic.object_id, ic.column_id) AS COLUMN_NAME
        FROM sys.indexes i
        INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        WHERE OBJECT_NAME(i.object_id) = '{table_name}'
        AND i.is_primary_key = 0
        AND i.name IS NOT NULL
        ORDER BY i.name, ic.key_ordinal
    """)
    return cursor.fetchall()

def get_check_constraints(cursor, table_name):
    """Get check constraints"""
    cursor.execute(f"""
        SELECT
            cc.name AS CONSTRAINT_NAME,
            cc.definition
        FROM sys.check_constraints cc
        WHERE OBJECT_NAME(cc.parent_object_id) = '{table_name}'
    """)
    return cursor.fetchall()

def get_unique_constraints(cursor, table_name):
    """Get unique constraints"""
    cursor.execute(f"""
        SELECT
            tc.CONSTRAINT_NAME,
            STRING_AGG(kcu.COLUMN_NAME, ', ') AS COLUMNS
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE tc.TABLE_NAME = '{table_name}'
        AND tc.CONSTRAINT_TYPE = 'UNIQUE'
        GROUP BY tc.CONSTRAINT_NAME
    """)
    return cursor.fetchall()

def get_views(cursor):
    """Get all views"""
    cursor.execute("""
        SELECT
            TABLE_NAME,
            VIEW_DEFINITION
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA = 'dbo'
        ORDER BY TABLE_NAME
    """)
    return cursor.fetchall()

def get_stored_procedures(cursor):
    """Get all stored procedures"""
    cursor.execute("""
        SELECT
            ROUTINE_NAME,
            ROUTINE_DEFINITION
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
        AND ROUTINE_SCHEMA = 'dbo'
        ORDER BY ROUTINE_NAME
    """)
    return cursor.fetchall()

def get_functions(cursor):
    """Get all functions"""
    cursor.execute("""
        SELECT
            ROUTINE_NAME,
            ROUTINE_DEFINITION
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'FUNCTION'
        AND ROUTINE_SCHEMA = 'dbo'
        ORDER BY ROUTINE_NAME
    """)
    return cursor.fetchall()

def main():
    print("=" * 60)
    print("MSIFactory Schema Extractor v7.0")
    print("=" * 60)
    print()

    # Connect to database
    conn = connect_to_database()
    cursor = conn.cursor()

    # Get all tables
    print("\n[INFO] Retrieving table list...")
    tables = get_all_tables(cursor)
    print(f"[OK] Found {len(tables)} tables")

    # Display table list
    print("\nTables found:")
    for table in tables:
        print(f"  - {table}")

    # Get schema information for each table
    print("\n[INFO] Extracting schema information...")

    schema_data = {
        'tables': {},
        'views': [],
        'procedures': [],
        'functions': []
    }

    for table in tables:
        print(f"  Processing {table}...")
        schema_data['tables'][table] = {
            'columns': get_table_schema(cursor, table),
            'primary_keys': get_primary_keys(cursor, table),
            'foreign_keys': get_foreign_keys(cursor, table),
            'indexes': get_indexes(cursor, table),
            'check_constraints': get_check_constraints(cursor, table),
            'unique_constraints': get_unique_constraints(cursor, table)
        }

    # Get views, procedures, functions
    print("\n[INFO] Retrieving views, procedures, and functions...")
    schema_data['views'] = get_views(cursor)
    schema_data['procedures'] = get_stored_procedures(cursor)
    schema_data['functions'] = get_functions(cursor)

    print(f"[OK] Found {len(schema_data['views'])} views")
    print(f"[OK] Found {len(schema_data['procedures'])} stored procedures")
    print(f"[OK] Found {len(schema_data['functions'])} functions")

    # Close connection
    conn.close()

    # Generate SQL file
    print("\n[INFO] Generating complete_schema_v7.sql...")
    generate_sql_file(schema_data)

    print("\n[SUCCESS] Schema extraction complete!")
    print(f"Output file: database/complete_schema_v7.sql")

def generate_sql_file(schema_data):
    """Generate the complete SQL schema file"""

    output_file = "complete_schema_v7.sql"

    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("-- " + "=" * 60 + "\n")
        f.write("-- MSI Factory Complete Database Schema for MS SQL Server\n")
        f.write("-- Version: 7.0 - PRODUCTION READY (Current State)\n")
        f.write(f"-- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- Description: Complete production schema extracted from current database\n")
        f.write("--              This reflects the ACTUAL current state of the database\n")
        f.write("-- " + "=" * 60 + "\n\n")

        f.write("SET NOCOUNT ON;\n")
        f.write("GO\n\n")

        # Database creation
        f.write("-- " + "=" * 60 + "\n")
        f.write("-- DATABASE CREATION\n")
        f.write("-- " + "=" * 60 + "\n")
        f.write("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')\n")
        f.write("BEGIN\n")
        f.write("    CREATE DATABASE MSIFactory;\n")
        f.write("END\n")
        f.write("GO\n\n")
        f.write("USE MSIFactory;\n")
        f.write("GO\n\n")

        # Tables
        f.write("-- " + "=" * 60 + "\n")
        f.write("-- TABLES\n")
        f.write("-- " + "=" * 60 + "\n\n")

        for table_name, table_info in schema_data['tables'].items():
            write_table_ddl(f, table_name, table_info)

        # Indexes
        f.write("\n-- " + "=" * 60 + "\n")
        f.write("-- INDEXES\n")
        f.write("-- " + "=" * 60 + "\n\n")

        for table_name, table_info in schema_data['tables'].items():
            write_indexes(f, table_name, table_info['indexes'])

        # Views
        if schema_data['views']:
            f.write("\n-- " + "=" * 60 + "\n")
            f.write("-- VIEWS\n")
            f.write("-- " + "=" * 60 + "\n\n")

            for view_name, view_def in schema_data['views']:
                f.write(f"-- View: {view_name}\n")
                f.write(f"IF EXISTS (SELECT * FROM sys.views WHERE name = '{view_name}')\n")
                f.write(f"    DROP VIEW {view_name};\n")
                f.write("GO\n\n")
                f.write(f"{view_def}\n")
                f.write("GO\n\n")

        # Stored Procedures
        if schema_data['procedures']:
            f.write("\n-- " + "=" * 60 + "\n")
            f.write("-- STORED PROCEDURES\n")
            f.write("-- " + "=" * 60 + "\n\n")

            for proc_name, proc_def in schema_data['procedures']:
                f.write(f"-- Procedure: {proc_name}\n")
                f.write(f"IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = '{proc_name}')\n")
                f.write(f"    DROP PROCEDURE {proc_name};\n")
                f.write("GO\n\n")
                f.write(f"{proc_def}\n")
                f.write("GO\n\n")

        # Functions
        if schema_data['functions']:
            f.write("\n-- " + "=" * 60 + "\n")
            f.write("-- FUNCTIONS\n")
            f.write("-- " + "=" * 60 + "\n\n")

            for func_name, func_def in schema_data['functions']:
                f.write(f"-- Function: {func_name}\n")
                f.write(f"IF EXISTS (SELECT * FROM sys.objects WHERE type = 'FN' AND name = '{func_name}')\n")
                f.write(f"    DROP FUNCTION {func_name};\n")
                f.write("GO\n\n")
                f.write(f"{func_def}\n")
                f.write("GO\n\n")

        # Footer
        f.write("\n-- " + "=" * 60 + "\n")
        f.write("-- SCHEMA EXTRACTION COMPLETE\n")
        f.write("-- " + "=" * 60 + "\n")
        f.write("SET NOCOUNT OFF;\n")

def write_table_ddl(f, table_name, table_info):
    """Write CREATE TABLE DDL"""
    f.write(f"-- Table: {table_name}\n")
    f.write(f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')\n")
    f.write("BEGIN\n")
    f.write(f"    CREATE TABLE {table_name} (\n")

    # Columns
    columns = []
    for col in table_info['columns']:
        col_name, data_type, max_len, precision, scale, is_null, default, is_identity = col

        col_def = f"        {col_name} "

        # Data type
        if data_type in ('varchar', 'char', 'nvarchar', 'nchar'):
            if max_len == -1:
                col_def += f"{data_type.upper()}(MAX)"
            else:
                col_def += f"{data_type.upper()}({max_len})"
        elif data_type in ('decimal', 'numeric'):
            col_def += f"{data_type.upper()}({precision}, {scale})"
        else:
            col_def += data_type.upper()

        # Identity
        if is_identity:
            col_def += " IDENTITY(1,1)"

        # Nullable
        if is_null == 'NO':
            col_def += " NOT NULL"

        # Default
        if default:
            col_def += f" DEFAULT {default}"

        columns.append(col_def)

    # Primary key
    if table_info['primary_keys']:
        pk_cols = ', '.join(table_info['primary_keys'])
        columns.append(f"        PRIMARY KEY ({pk_cols})")

    f.write(",\n".join(columns))
    f.write("\n    );\n")
    f.write("END\n")
    f.write("GO\n\n")

    # Foreign keys
    for fk in table_info['foreign_keys']:
        fk_name, tbl, col, ref_tbl, ref_col, del_action, upd_action = fk
        f.write(f"-- Add foreign key: {fk_name}\n")
        f.write(f"IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = '{fk_name}')\n")
        f.write(f"BEGIN\n")
        f.write(f"    ALTER TABLE {table_name}\n")
        f.write(f"    ADD CONSTRAINT {fk_name}\n")
        f.write(f"    FOREIGN KEY ({col}) REFERENCES {ref_tbl}({ref_col})")

        if del_action != 'NO_ACTION':
            f.write(f" ON DELETE {del_action}")
        if upd_action != 'NO_ACTION':
            f.write(f" ON UPDATE {upd_action}")

        f.write(";\n")
        f.write("END\n")
        f.write("GO\n\n")

    # Check constraints
    for constraint_name, definition in table_info['check_constraints']:
        f.write(f"-- Add check constraint: {constraint_name}\n")
        f.write(f"IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = '{constraint_name}')\n")
        f.write(f"BEGIN\n")
        f.write(f"    ALTER TABLE {table_name}\n")
        f.write(f"    ADD CONSTRAINT {constraint_name} CHECK {definition};\n")
        f.write("END\n")
        f.write("GO\n\n")

    # Unique constraints
    for constraint_name, columns in table_info['unique_constraints']:
        f.write(f"-- Add unique constraint: {constraint_name}\n")
        f.write(f"IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = '{constraint_name}')\n")
        f.write(f"BEGIN\n")
        f.write(f"    ALTER TABLE {table_name}\n")
        f.write(f"    ADD CONSTRAINT {constraint_name} UNIQUE ({columns});\n")
        f.write("END\n")
        f.write("GO\n\n")

def write_indexes(f, table_name, indexes):
    """Write CREATE INDEX statements"""
    if not indexes:
        return

    # Group indexes by name
    idx_groups = {}
    for idx_name, is_unique, col_name in indexes:
        if idx_name not in idx_groups:
            idx_groups[idx_name] = {'is_unique': is_unique, 'columns': []}
        idx_groups[idx_name]['columns'].append(col_name)

    for idx_name, idx_info in idx_groups.items():
        f.write(f"-- Index: {idx_name}\n")
        f.write(f"IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = '{idx_name}')\n")
        f.write("BEGIN\n")

        unique_str = "UNIQUE " if idx_info['is_unique'] else ""
        cols = ', '.join(idx_info['columns'])

        f.write(f"    CREATE {unique_str}INDEX {idx_name}\n")
        f.write(f"    ON {table_name} ({cols});\n")
        f.write("END\n")
        f.write("GO\n\n")

if __name__ == "__main__":
    main()
