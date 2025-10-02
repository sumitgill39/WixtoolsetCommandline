"""
JFrog Polling System - Configuration Setup Helper
Interactive script to configure JFrog credentials and system settings
"""

import getpass
from db_helper import DatabaseHelper


def setup_jfrog_config():
    """Interactive setup for JFrog configuration"""
    print("=" * 60)
    print("JFrog Polling System - Configuration Setup")
    print("=" * 60)
    print()

    # Connect to database
    db = DatabaseHelper()
    print("Connecting to database...")

    if not db.connect():
        print("ERROR: Failed to connect to database")
        print("Please check your database connection settings in db_helper.py")
        return

    print("✓ Database connected successfully")
    print()

    # Get current configuration
    print("Current Configuration:")
    print("-" * 60)

    current_url = db.get_system_config('JFrogBaseURL') or 'Not set'
    current_user = db.get_system_config('SVCJFROGUSR') or 'Not set'
    current_base_drive = db.get_system_config('BaseDrive') or 'Not set'
    current_max_threads = db.get_system_config('MaxConcurrentThreads') or 'Not set'
    current_max_builds = db.get_system_config('MaxBuildsToKeep') or 'Not set'

    print(f"JFrog Base URL: {current_url}")
    print(f"JFrog Username: {current_user}")
    print(f"JFrog Password: {'****' if current_user != 'Not set' else 'Not set'}")
    print(f"Base Drive: {current_base_drive}")
    print(f"Max Concurrent Threads: {current_max_threads}")
    print(f"Max Builds to Keep: {current_max_builds}")
    print()

    # Prompt for new configuration
    print("Enter new configuration (press Enter to keep current value):")
    print("-" * 60)

    # JFrog Base URL
    new_url = input(f"JFrog Base URL [{current_url}]: ").strip()
    if new_url:
        db.update_system_config('JFrogBaseURL', new_url, 'setup_script')
        print(f"✓ JFrog Base URL updated to: {new_url}")

    # JFrog Username
    new_username = input(f"JFrog Username [{current_user}]: ").strip()
    if new_username:
        db.update_system_config('SVCJFROGUSR', new_username, 'setup_script')
        print(f"✓ JFrog Username updated to: {new_username}")

    # JFrog Password
    update_password = input("Update JFrog Password? (y/n) [n]: ").strip().lower()
    if update_password == 'y':
        new_password = getpass.getpass("JFrog Password: ")
        if new_password:
            db.update_system_config('SVCJFROGPAS', new_password, 'setup_script')
            print("✓ JFrog Password updated")

    print()
    print("System Configuration:")
    print("-" * 60)

    # Base Drive
    new_base_drive = input(f"Base Drive for artifacts [{current_base_drive}]: ").strip()
    if new_base_drive:
        db.update_system_config('BaseDrive', new_base_drive, 'setup_script')
        print(f"✓ Base Drive updated to: {new_base_drive}")

    # Max Concurrent Threads
    new_max_threads = input(f"Max Concurrent Threads (1-10000) [{current_max_threads}]: ").strip()
    if new_max_threads:
        try:
            threads = int(new_max_threads)
            if 1 <= threads <= 10000:
                db.update_system_config('MaxConcurrentThreads', str(threads), 'setup_script')
                print(f"✓ Max Concurrent Threads updated to: {threads}")
            else:
                print("✗ Invalid value. Must be between 1 and 10000")
        except ValueError:
            print("✗ Invalid value. Must be a number")

    # Max Builds to Keep
    new_max_builds = input(f"Max Builds to Keep per Component/Branch [{current_max_builds}]: ").strip()
    if new_max_builds:
        try:
            builds = int(new_max_builds)
            if builds >= 1:
                db.update_system_config('MaxBuildsToKeep', str(builds), 'setup_script')
                print(f"✓ Max Builds to Keep updated to: {builds}")
            else:
                print("✗ Invalid value. Must be at least 1")
        except ValueError:
            print("✗ Invalid value. Must be a number")

    print()
    print("=" * 60)
    print("Configuration Update Complete!")
    print("=" * 60)
    print()

    # Test JFrog connection
    test_connection = input("Test JFrog connection now? (y/n) [y]: ").strip().lower()
    if test_connection != 'n':
        print()
        print("Testing JFrog connection...")

        from jfrog_config import JFrogConfig

        jfrog = JFrogConfig(db)
        success, message = jfrog.test_connection()

        if success:
            print(f"✓ Connection test successful: {message}")
        else:
            print(f"✗ Connection test failed: {message}")
            print()
            print("Please verify your JFrog credentials and URL")

    # Disconnect
    db.disconnect()
    print()
    print("Setup complete. You can now run the polling system.")
    print()
    print("Quick Start Commands:")
    print("  python jfrog_polling_main.py status   # Check system status")
    print("  python jfrog_polling_main.py poll     # Run single poll cycle")
    print("  python jfrog_polling_main.py start    # Start continuous polling")


if __name__ == '__main__':
    try:
        setup_jfrog_config()
    except KeyboardInterrupt:
        print()
        print("Setup cancelled by user")
    except Exception as e:
        print(f"ERROR: {str(e)}")
