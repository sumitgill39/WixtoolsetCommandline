#!/usr/bin/env python3
"""
Test script to verify login and project deletion fixes
"""

import sys
sys.path.append('.')

from auth.simple_auth import SimpleAuth
from logger import get_logger

def test_authentication():
    """Test authentication functionality"""
    print("Testing Authentication...")

    auth = SimpleAuth()

    # Test admin login
    admin_user = auth.check_user_login("admin", "COMPANY")
    if admin_user and admin_user['status'] == 'approved':
        print("✓ Admin login works")
        print(f"  User: {admin_user['username']}, Role: {admin_user['role']}")
    else:
        print("✗ Admin login failed")
        return False

    # Test regular user login
    user = auth.check_user_login("john.doe", "COMPANY")
    if user and user['status'] == 'approved':
        print("✓ Regular user login works")
        print(f"  User: {user['username']}, Role: {user['role']}")
    else:
        print("✗ Regular user login failed")
        return False

    return True

def test_project_deletion():
    """Test project deletion functionality"""
    print("\nTesting Project Deletion...")

    auth = SimpleAuth()

    # Get current projects
    projects_before = auth.load_projects()
    print(f"Projects before deletion: {len(projects_before)}")

    if len(projects_before) == 0:
        print("✗ No projects to delete")
        return False

    # Try to delete first project
    project_to_delete = projects_before[0]['project_id']
    print(f"Attempting to delete project ID: {project_to_delete}")

    success, message = auth.delete_project(project_to_delete)

    if success:
        print(f"✓ Project deletion successful: {message}")

        # Verify deletion
        projects_after = auth.load_projects()
        print(f"Projects after deletion: {len(projects_after)}")

        if len(projects_after) == len(projects_before) - 1:
            print("✓ Project count decreased correctly")

            # Restore the project for future tests
            projects_before_restore = auth.load_projects()
            projects_before_restore.append(projects_before[0])
            auth.save_projects(projects_before_restore)
            print("✓ Project restored for future tests")

            return True
        else:
            print("✗ Project count didn't decrease")
            return False
    else:
        print(f"✗ Project deletion failed: {message}")
        return False

def test_logging():
    """Test logging functionality"""
    print("\nTesting Logging...")

    try:
        logger = get_logger()

        # Test different log types
        logger.log_system_event("TEST", "Testing system logging")
        logger.log_user_login("test_user", success=True, ip_address="127.0.0.1")
        logger.log_user_login("test_user", success=False, ip_address="127.0.0.1")
        logger.log_security_violation("TEST_VIOLATION", "test_user", "Test violation details")

        print("✓ All logging functions executed without errors")
        return True

    except Exception as e:
        print(f"✗ Logging failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=== MSI Factory Fixes Test ===\n")

    results = []

    # Test authentication
    results.append(test_authentication())

    # Test project deletion
    results.append(test_project_deletion())

    # Test logging
    results.append(test_logging())

    print(f"\n=== Test Results ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("✓ All tests passed! Login and project deletion should work correctly.")
    else:
        print("✗ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()