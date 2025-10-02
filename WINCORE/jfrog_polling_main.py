"""
JFrog Multi-threaded Polling System - Main Orchestrator
Entry point for the JFrog artifact polling, download, and extraction system

Usage:
    python jfrog_polling_main.py start              # Start continuous polling
    python jfrog_polling_main.py poll               # Run single poll cycle
    python jfrog_polling_main.py test               # Test JFrog connection
    python jfrog_polling_main.py cleanup            # Run cleanup for all components
    python jfrog_polling_main.py status             # Show system status
    python jfrog_polling_main.py config             # Show configuration
"""

import sys
import argparse
import logging
from datetime import datetime
from db_helper import DatabaseHelper
from jfrog_config import JFrogConfig
from polling_engine import PollingEngine
from cleanup_manager import CleanupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'jfrog_polling_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JFrogPollingOrchestrator:
    """Main orchestrator for JFrog polling system"""

    def __init__(self):
        """Initialize orchestrator"""
        self.db = DatabaseHelper()
        self.jfrog_config = None
        self.polling_engine = None
        self.cleanup_manager = None

    def connect_database(self) -> bool:
        """Connect to database"""
        logger.info("Connecting to database...")
        if self.db.connect():
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection failed")
            return False

    def initialize_components(self):
        """Initialize all system components"""
        logger.info("Initializing system components...")

        self.jfrog_config = JFrogConfig(self.db)
        self.polling_engine = PollingEngine(self.db)
        self.cleanup_manager = CleanupManager(self.db)

        logger.info("System components initialized")

    def test_connection(self):
        """Test JFrog connection"""
        logger.info("=" * 60)
        logger.info("Testing JFrog Connection")
        logger.info("=" * 60)

        if not self.jfrog_config:
            self.initialize_components()

        success, message = self.jfrog_config.test_connection()

        if success:
            logger.info(f"✓ Connection test successful: {message}")
            print("\n✓ JFrog connection test PASSED")
        else:
            logger.error(f"✗ Connection test failed: {message}")
            print(f"\n✗ JFrog connection test FAILED: {message}")

        return success

    def show_configuration(self):
        """Display current configuration"""
        logger.info("=" * 60)
        logger.info("System Configuration")
        logger.info("=" * 60)

        base_url, username, _ = self.db.get_jfrog_credentials()
        base_drive = self.db.get_base_drive()
        max_threads = self.db.get_max_threads()
        max_builds = self.db.get_max_builds_to_keep()

        config_info = f"""
        JFrog Configuration:
        - Base URL: {base_url or 'Not configured'}
        - Username: {username or 'Not configured'}
        - Password: {'****' if username else 'Not configured'}

        System Configuration:
        - Base Drive: {base_drive}
        - Max Concurrent Threads: {max_threads}
        - Max Builds to Keep: {max_builds}
        """

        print(config_info)
        logger.info(config_info)

    def show_status(self):
        """Show system status"""
        logger.info("=" * 60)
        logger.info("System Status")
        logger.info("=" * 60)

        # Get active polling configurations
        configs = self.db.get_active_polling_config()

        status_info = f"""
        Active Components: {len(configs)}
        Database: Connected
        JFrog: {'Connected' if self.jfrog_config and self.jfrog_config.session else 'Not connected'}
        """

        print(status_info)
        logger.info(status_info)

        # Show active component details
        if configs:
            print("\nActive Component/Branch Configurations:")
            print("-" * 80)
            print(f"{'Component':<30} {'Branch':<20} {'Last Build':<30}")
            print("-" * 80)

            for config in configs:
                component_name = config.get('component_name', 'N/A')
                branch_name = config.get('branch_name', 'N/A')
                last_build = f"Build{config.get('latest_build_date', 'N/A')}.{config.get('latest_build_number', 'N/A')}"
                print(f"{component_name:<30} {branch_name:<20} {last_build:<30}")

    def run_single_poll(self):
        """Run a single polling cycle"""
        logger.info("=" * 60)
        logger.info(f"Starting Single Poll Cycle at {datetime.now()}")
        logger.info("=" * 60)

        if not self.polling_engine:
            self.initialize_components()

        self.polling_engine.start()
        results = self.polling_engine.poll_all_components()
        self.polling_engine.stop()

        # Display results summary
        successful = sum(1 for r in results if r.get('success'))
        new_builds = sum(1 for r in results if r.get('new_build'))
        failed = sum(1 for r in results if not r.get('success'))

        summary = f"""
        Poll Cycle Summary:
        - Total Components Polled: {len(results)}
        - Successful: {successful}
        - New Builds Found: {new_builds}
        - Failed: {failed}
        """

        print(summary)
        logger.info(summary)

        # Show new builds details
        if new_builds > 0:
            print("\nNew Builds Detected:")
            print("-" * 80)
            for result in results:
                if result.get('new_build'):
                    component_id = result.get('component_id')
                    build_date = result.get('build_date')
                    build_number = result.get('build_number')
                    print(f"  - Component ID {component_id}: Build{build_date}.{build_number}")

    def run_continuous_polling(self):
        """Run continuous polling"""
        logger.info("=" * 60)
        logger.info("Starting Continuous Polling Mode")
        logger.info("=" * 60)

        if not self.polling_engine:
            self.initialize_components()

        # Get default polling frequency
        default_frequency = int(self.db.get_system_config('DefaultPollingFrequency') or 300)

        logger.info(f"Polling frequency: {default_frequency} seconds")
        print(f"\nStarting continuous polling (every {default_frequency} seconds)")
        print("Press Ctrl+C to stop\n")

        try:
            self.polling_engine.run_continuous_polling(default_frequency)
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
            print("\nPolling stopped by user")

    def run_cleanup(self):
        """Run cleanup for all components"""
        logger.info("=" * 60)
        logger.info("Starting Cleanup Process")
        logger.info("=" * 60)

        if not self.cleanup_manager:
            self.initialize_components()

        result = self.cleanup_manager.cleanup_all_components()

        if result['success']:
            summary = f"""
            Cleanup Summary:
            - Components Processed: {result['components_processed']}
            - Total Items Deleted: {result['total_deleted']}
            - Total Items Failed: {result['total_failed']}
            - Space Freed: {result['total_space_freed'] / (1024*1024):.2f} MB
            """
            print(summary)
            logger.info(summary)
        else:
            error_msg = f"Cleanup failed: {result.get('error')}"
            print(error_msg)
            logger.error(error_msg)

    def run(self, command: str):
        """Run specified command"""
        # Connect to database
        if not self.connect_database():
            print("ERROR: Failed to connect to database")
            sys.exit(1)

        # Initialize components
        self.initialize_components()

        # Execute command
        if command == 'test':
            self.test_connection()

        elif command == 'config':
            self.show_configuration()

        elif command == 'status':
            self.show_status()

        elif command == 'poll':
            self.run_single_poll()

        elif command == 'start':
            self.run_continuous_polling()

        elif command == 'cleanup':
            self.run_cleanup()

        else:
            print(f"Unknown command: {command}")
            print("Use --help for available commands")

        # Disconnect database
        self.db.disconnect()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='JFrog Multi-threaded Polling System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start     - Start continuous polling (default every 5 minutes)
  poll      - Run a single poll cycle
  test      - Test JFrog connection
  cleanup   - Run cleanup for all components (keep last 5 builds)
  status    - Show system status
  config    - Show configuration

Examples:
  python jfrog_polling_main.py start
  python jfrog_polling_main.py poll
  python jfrog_polling_main.py test
  python jfrog_polling_main.py cleanup
        """
    )

    parser.add_argument(
        'command',
        choices=['start', 'poll', 'test', 'cleanup', 'status', 'config'],
        help='Command to execute'
    )

    args = parser.parse_args()

    # Create and run orchestrator
    orchestrator = JFrogPollingOrchestrator()

    try:
        orchestrator.run(args.command)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\nFATAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
