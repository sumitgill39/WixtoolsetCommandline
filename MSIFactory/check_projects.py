import pyodbc

# Simple script to check what projects exist
try:
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
        "DATABASE=MSIFactory;"
        "Trusted_Connection=yes;"
    )

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("SELECT project_id, project_name, project_key, status FROM projects ORDER BY project_id")
    projects = cursor.fetchall()

    print("Existing projects:")
    for project in projects:
        print(f"ID: {project[0]}, Name: {project[1]}, Key: {project[2]}, Status: {project[3]}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")