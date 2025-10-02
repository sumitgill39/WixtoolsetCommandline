import pyodbc

def test_connection():
    try:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes"
        )
        print("Attempting to connect to SQL Server...")
        conn = pyodbc.connect(conn_str)
        print("Connection successful!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print(f"\nSQL Server Version:\n{row[0]}")
        
        cursor.close()
        conn.close()
        print("\nConnection closed successfully.")
        return True
    except Exception as e:
        print(f"\nError connecting to database: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()