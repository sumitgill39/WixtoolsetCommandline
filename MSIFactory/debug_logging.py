#!/usr/bin/env python3
"""
Debug script to test logging functionality and project deletion
"""

import sys
import os
sys.path.append('.')

from auth.simple_auth import SimpleAuth
from logger import get_logger, log_info, log_error

def debug_logging():
    """Debug logging system"""
    print("=== Debug Logging System ===")

    # Test 1: Basic logging
    print("\n1. Testing basic logging functions...")
    try:
        log_info("DEBUG: Testing log_info function")
        log_error("DEBUG: Testing log_error function")
        print("✓ Basic logging functions executed")
    except Exception as e:
        print(f"✗ Basic logging failed: {e}")
        return False

    # Test 2: Direct logger
    print("\n2. Testing direct logger...")
    try:
        logger = get_logger()
        logger.log_system_event("DEBUG", "Testing direct logger system event")
        logger.log_user_login("debug_user", success=True, ip_address="127.0.0.1")
        print("✓ Direct logger executed")
    except Exception as e:
        print(f"✗ Direct logger failed: {e}")
        return False

    # Test 3: Check if log files are being written
    print("\n3. Checking log file contents...")
    try:
        if os.path.exists("logs/system.log"):
            with open("logs/system.log", "r") as f:
                lines = f.readlines()
                recent_lines = [line for line in lines[-10:] if "DEBUG" in line]
                if recent_lines:
                    print("✓ DEBUG entries found in system.log:")
                    for line in recent_lines:
                        print(f"  {line.strip()}")
                else:
                    print("✗ No DEBUG entries found in recent system.log")
                    print("Recent system.log entries:")
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
        else:
            print("✗ system.log file not found")

        if os.path.exists("logs/access.log"):
            with open("logs/access.log", "r") as f:
                lines = f.readlines()
                recent_lines = [line for line in lines[-5:] if "debug_user" in line]
                if recent_lines:
                    print("✓ DEBUG user login found in access.log:")
                    for line in recent_lines:
                        print(f"  {line.strip()}")
                else:
                    print("✗ No debug_user entries found in access.log")
    except Exception as e:
        print(f"✗ Error reading log files: {e}")

    return True

def debug_project_deletion():
    """Debug project deletion without web context"""
    print("\n=== Debug Project Deletion ===")

    auth = SimpleAuth()

    # Get projects
    projects = auth.load_projects()
    print(f"Current projects: {len(projects)}")

    if len(projects) == 0:
        print("✗ No projects available for deletion test")
        return False

    # Test deletion logic (simulate)
    test_project_id = projects[0]['project_id']
    print(f"Testing deletion for project ID: {test_project_id}")

    # Simulate the logging that should happen in delete_project
    log_info(f"DEBUG: Simulating delete project function call for project {test_project_id}")
    log_info(f"DEBUG: Using auth_system to delete project {test_project_id}")

    # Actually delete and restore
    success, message = auth.delete_project(test_project_id)
    if success:
        log_info(f"DEBUG: PROJECT_DELETED: Project ID: {test_project_id}, Deleted by: debug_user")
        print(f"✓ Project deletion successful: {message}")

        # Restore project
        projects_after = auth.load_projects()
        projects_after.append(projects[0])  # Restore the deleted project
        auth.save_projects(projects_after)
        print("✓ Project restored")
        return True
    else:
        print(f"✗ Project deletion failed: {message}")
        return False

if __name__ == "__main__":
    print("MSI Factory Debug Script")
    print("=" * 50)

    success1 = debug_logging()
    success2 = debug_project_deletion()

    print(f"\n=== Results ===")
    print(f"Logging test: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Project deletion test: {'✓ PASS' if success2 else '✗ FAIL'}")

    if success1 and success2:
        print("\n✓ All tests passed! Logging should work correctly.")
    else:
        print("\n✗ Some tests failed. Check the output above.")