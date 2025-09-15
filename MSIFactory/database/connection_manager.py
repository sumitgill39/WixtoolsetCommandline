#!/usr/bin/env python3
"""
Simple Database Connection Manager
"""

import time
import sys
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import get_config

config = get_config()()
connection_string = config.database_url

engine = create_engine(connection_string, echo=config.SQLALCHEMY_ECHO, poolclass=None)
SessionFactory = sessionmaker(bind=engine)

def test_database_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print(f"[OK] Database connection test successful")
                return True
    except Exception as e:
        print(f"[ERROR] Database connection test failed: {e}")
        return False

@contextmanager
def get_robust_session():
    """Get database session"""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Database session error: {e}")
        raise
    finally:
        session.close()

def execute_with_retry(operation, *args, **kwargs):
    """Execute database operation"""
    with get_robust_session() as session:
        return operation(session, *args, **kwargs)

def get_db_connection_info():
    """Get database connection information"""
    return {
        'server': config.DB_SERVER,
        'database': config.DB_NAME,
        'driver': config.DB_DRIVER,
        'authentication': 'Windows' if not config.DB_USERNAME else 'SQL Server'
    }

if __name__ == '__main__':
    print("Testing Database Connection Manager...")
    
    if test_database_connection():
        print("[OK] Database connection test passed")
        
        info = get_db_connection_info()
        print("\nDatabase Connection Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("[ERROR] Database connection test failed")
    
    print("\nConnection manager test completed.")