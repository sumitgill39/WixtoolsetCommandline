#!/usr/bin/env python3
"""
Test project deletion functionality directly
"""

import sys
import os
sys.path.append('.')

from auth.simple_auth import SimpleAuth
from logger import get_logger, log_info, log_error

def test_project_deletion():
    """Test project deletion with an existing project"""
    print("=== Testing Project Deletion ===")

    # Initialize auth system
    auth = SimpleAuth()

    # Load current projects
    projects_before = auth.load_projects()
    print(f"Projects before deletion: {len(projects_before)}")

    for project in projects_before:
        print(f"  - ID: {project['project_id']}, Name: {project['project_name']}")

    if len(projects_before) == 0:
        print("✗ No projects available to test deletion")
        return False

    # Test deletion with project ID 1 (which exists)
    test_project_id = 1
    print(f"\nTesting deletion of project ID: {test_project_id}")

    # Simulate the logging that happens in the main app
    log_info(f"TEST: Delete project function called by user: test_user")
    log_info(f"TEST: No API client available, using auth_system to delete project {test_project_id}")

    # Perform the deletion
    success, message = auth.delete_project(test_project_id)

    if success:
        log_info(f"TEST: PROJECT_DELETED: Project ID: {test_project_id}, Deleted by: test_user")
        print(f"✓ Project deletion successful: {message}")

        # Verify deletion
        projects_after = auth.load_projects()
        print(f"Projects after deletion: {len(projects_after)}")

        if len(projects_after) == len(projects_before) - 1:
            print("✓ Project count decreased correctly")

            # Check that the specific project was removed
            deleted_project_exists = any(p['project_id'] == test_project_id for p in projects_after)
            if not deleted_project_exists:
                print(f"✓ Project ID {test_project_id} was successfully removed")

                # Restore the project for future testing
                projects_after.append(projects_before[0])  # Add back the first project
                auth.save_projects(projects_after)
                print("✓ Project restored for future testing")

                return True
            else:
                print(f"✗ Project ID {test_project_id} still exists after deletion")
                return False
        else:
            print("✗ Project count didn't decrease as expected")
            return False
    else:
        log_error(f"TEST: PROJECT_DELETE_FAILED: Project ID: {test_project_id}, Error: {message}")
        print(f"✗ Project deletion failed: {message}")
        return False

def test_nonexistent_project_deletion():
    """Test deletion of non-existent project"""
    print("\n=== Testing Non-existent Project Deletion ===")

    auth = SimpleAuth()

    # Try to delete project ID 10 (doesn't exist)
    test_project_id = 10
    print(f"Testing deletion of non-existent project ID: {test_project_id}")

    log_info(f"TEST: Delete project function called by user: test_user")
    log_info(f"TEST: No API client available, using auth_system to delete project {test_project_id}")

    success, message = auth.delete_project(test_project_id)

    if not success and "not found" in message.lower():
        log_error(f"TEST: PROJECT_DELETE_FAILED: Project ID: {test_project_id}, Error: {message}")
        print(f"✓ Non-existent project deletion handled correctly: {message}")
        return True
    else:
        print(f"✗ Unexpected result for non-existent project: success={success}, message={message}")
        return False

def check_recent_logs():
    """Check if the test logs were written"""
    print("\n=== Checking Recent Logs ===")

    try:
        if os.path.exists("logs/system.log"):
            with open("logs/system.log", "r") as f:
                lines = f.readlines()
                test_lines = [line for line in lines[-20:] if "TEST:" in line]

                if test_lines:
                    print("✓ Test log entries found:")
                    for line in test_lines:
                        print(f"  {line.strip()}")
                else:
                    print("✗ No test log entries found in recent logs")
                    print("Recent log entries:")
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
        else:
            print("✗ system.log file not found")
    except Exception as e:
        print(f"✗ Error reading logs: {e}")

if __name__ == "__main__":
    print("MSI Factory Project Deletion Test")
    print("=" * 50)

    success1 = test_project_deletion()
    success2 = test_nonexistent_project_deletion()

    check_recent_logs()

    print(f"\n=== Test Results ===")
    print(f"Existing project deletion: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Non-existent project deletion: {'✓ PASS' if success2 else '✗ FAIL'}")

    if success1 and success2:
        print("\n✓ All tests passed! Project deletion is working correctly.")
    else:
        print("\n✗ Some tests failed. Check the output above.")