#!/usr/bin/env python3
"""
Test script to check logging functionality
"""

import sys
import os
sys.path.append('.')

from logger import get_logger, log_info, log_error

def test_direct_logging():
    """Test logging functions directly"""
    print("Testing logging functions...")

    try:
        # Test log_info function (used in project deletion)
        print("Testing log_info...")
        log_info("TEST: Project deletion logging test")

        # Test direct logger
        print("Testing direct logger...")
        logger = get_logger()
        logger.log_system_event("TEST", "Direct logger test")

        # Check if logs were created
        print("Checking log files...")

        if os.path.exists("logs/system.log"):
            with open("logs/system.log", "r") as f:
                lines = f.readlines()
                recent_lines = lines[-5:]
                print("Recent system log entries:")
                for line in recent_lines:
                    print(f"  {line.strip()}")
        else:
            print("ERROR: system.log not found")

        print("Logging test completed")

    except Exception as e:
        print(f"ERROR in logging test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_logging()