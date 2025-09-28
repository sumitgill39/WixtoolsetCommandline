"""
Test script to verify SQL-only authentication
"""

import sys
sys.path.append('core')

from core.database_operations import authenticate_user_sql, get_user_by_username_sql

def test_sql_authentication():
    """Test SQL-based authentication"""
    print("\n" + "="*60)
    print("Testing SQL-Only Authentication")
    print("="*60)

    # Test admin authentication
    print("\nTesting admin login...")
    user_data, message = authenticate_user_sql('admin', 'password123')
    if user_data:
        print(f"[OK] Admin login successful: {user_data['username']} ({user_data['role']})")
    else:
        print(f"[FAIL] Admin login failed: {message}")

    # Test regular user authentication
    print("\nTesting john.doe login...")
    user_data, message = authenticate_user_sql('john.doe', 'password123')
    if user_data:
        print(f"[OK] User login successful: {user_data['username']} ({user_data['role']})")
    else:
        print(f"[FAIL] User login failed: {message}")

    # Test wrong password
    print("\nTesting wrong password...")
    user_data, message = authenticate_user_sql('admin', 'wrongpassword')
    if user_data:
        print(f"[FAIL] Login should have failed but succeeded: {user_data}")
    else:
        print(f"[OK] Wrong password correctly rejected: {message}")

    # Test nonexistent user
    print("\nTesting nonexistent user...")
    user_data, message = authenticate_user_sql('nonexistent', 'password123')
    if user_data:
        print(f"[FAIL] Login should have failed but succeeded: {user_data}")
    else:
        print(f"[OK] Nonexistent user correctly rejected: {message}")

    # Test get user by username
    print("\nTesting get user by username...")
    user_data = get_user_by_username_sql('john.doe')
    if user_data:
        print(f"[OK] User found: {user_data['username']} ({user_data['email']})")
    else:
        print("[FAIL] User not found")

    print("\n" + "="*60)
    print("Authentication test complete")
    print("="*60)

if __name__ == "__main__":
    test_sql_authentication()