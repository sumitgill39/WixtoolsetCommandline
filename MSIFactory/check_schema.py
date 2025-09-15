#!/usr/bin/env python3
"""
Check Database Schema - Verify column structure
"""

import pyodbc

# Direct connection to MS SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
    "DATABASE=MSIFactory;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=== Projects Table Schema ===")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'projects'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    for i, col in enumerate(columns):
        print(f"{i:2d}: {col[0]} ({col[1]}{'(' + str(col[2]) + ')' if col[2] else ''}) {'NULL' if col[3] == 'YES' else 'NOT NULL'}")
    
    print("\n=== Project Environments Table Schema ===")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'project_environments'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    for i, col in enumerate(columns):
        print(f"{i:2d}: {col[0]} ({col[1]}{'(' + str(col[2]) + ')' if col[2] else ''}) {'NULL' if col[3] == 'YES' else 'NOT NULL'}")
    
    print("\n=== Sample Data Check ===")
    cursor.execute("SELECT TOP 1 * FROM projects ORDER BY project_id DESC")
    project = cursor.fetchone()
    
    if project:
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'projects'
            ORDER BY ORDINAL_POSITION
        """)
        column_names = [row[0] for row in cursor.fetchall()]
        
        print("\nLatest Project Data:")
        for i, (col_name, value) in enumerate(zip(column_names, project)):
            print(f"  {col_name}: {value}")
    
except Exception as e:
    print(f"\n[ERROR] Schema check failed: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    if 'conn' in locals():
        conn.close()
        print("\nDatabase connection closed")