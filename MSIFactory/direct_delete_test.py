#!/usr/bin/env python3
"""
Direct test of project deletion to verify functionality
"""

import sys
import os
sys.path.append('.')

from auth.simple_auth import SimpleAuth
from logger import log_info, log_error

# Test deletion of project ID 1
auth = SimpleAuth()

print("Before deletion:")
projects = auth.load_projects()
for p in projects:
    print(f"  Project {p['project_id']}: {p['project_name']}")

print(f"\nTotal projects: {len(projects)}")

# Log the deletion attempt
log_info("DIRECT_TEST: Delete project function called by user: direct_test")
log_info("DIRECT_TEST: No API client available, using auth_system to delete project 1")

# Attempt to delete project 1
success, message = auth.delete_project(1)

if success:
    log_info("DIRECT_TEST: PROJECT_DELETED: Project ID: 1, Deleted by: direct_test")
    print(f"\n✓ SUCCESS: {message}")

    # Check result
    projects_after = auth.load_projects()
    print(f"\nAfter deletion - Total projects: {len(projects_after)}")
    for p in projects_after:
        print(f"  Project {p['project_id']}: {p['project_name']}")

    # Restore the project
    projects_after.append(projects[0])
    auth.save_projects(projects_after)
    print("\n✓ Project restored")

else:
    log_error(f"DIRECT_TEST: PROJECT_DELETE_FAILED: Project ID: 1, Error: {message}")
    print(f"\n✗ FAILED: {message}")

print("\nCheck logs/system.log for DIRECT_TEST entries")