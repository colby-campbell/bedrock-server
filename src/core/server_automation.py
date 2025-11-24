from utils import BufferedDailyLogger, LineBroadcaster, get_prefix, LogLevel
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
import threading
import shutil

# Constants
RESTART_WARNING_MINUTES = 5
CRASH_DETECTION_WINDOW_MINUTES = 10
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"

"""
This will need to manage server automation tasks like
- Scheduled restarts (DONE!)
- Automated Backups (DONE!)
    - Auto-delete old backups based on backup_duration setting (DONE!)
    - Notify users before backups/restarts (DONE!)
- Update checks (like for new versions of the server software)
- Logging (DONE!)
- Optional reboot on crash or extended server downtime (DONE! well not the downtime part)
- Queue or buffer output?

Next to do:
    - Scheduled restarts
        - Most likely I will use the same idea as I did years ago, creating a thread and sleeping it until the desired time
        - This will work just fine for my use-case compared to interval checking (not necessary and a little overkill checking every minute),
            or a non-standard library (kind of overkill and I don't want another dependency).
"""


class ServerAutomation:
    def __init__(self, config, runner):
        self.config = config
        self.runner = runner
        # Subscribe to the stdout broadcaster and unexpected shutdown broadcaster
        self.runner.stdout_broadcaster.subscribe(self.handle_server_output)
        self.runner.unexpected_shutdown_broadcaster.subscribe(self.handle_unexpected_shutdown)
        # Create a broadcaster to broadcast outputs to the CLI
        self.automation_output_broadcaster = LineBroadcaster()
        # Create logger
        self.logger = BufferedDailyLogger(self.config.log_loc)
        # Create a list of crashes
        self.recent_crashes = []


    def start(self):
        """Start the server automation tasks that require threads."""
        # Start the scheduled restart thread
        scheduled_restart_thread = threading.Thread(target=self._scheduled_restart, daemon=True)
        scheduled_restart_thread.start()


    def handle_server_output(self, timestamp, line):
        """Process server output lines for automation triggers.
        Args:
            timestamp (str): The timestamp of the output line.
            line (str): The output line from the server.
        """
        self.logger.log(timestamp + line)


    def handle_unexpected_shutdown(self, timestamp, line):
        """Handle unexpected server shutdowns.
        Args:
            timestamp (str): The timestamp of the shutdown event.
            line (str): The output line indicating the shutdown.
        """
        # Log the unexpected shutdown
        self.logger.log(timestamp + line)
        self.automation_output_broadcaster.publish(timestamp, line)
        # Add the crash time to the list of crashes
        now = datetime.now()
        self.recent_crashes.append(now)
        crash_detection_window = now - timedelta(minutes=CRASH_DETECTION_WINDOW_MINUTES)
        # If any of the timestamps are older than the CRASH_DETECTION_WINDOW_MINUTES minutes, remove them
        for time in self.recent_crashes:
            if time < crash_detection_window:
                self.recent_crashes.pop
        # If the length is larger than the crash limit, send an error and do not restart the server
        if len(self.recent_crashes) >= self.config.crash_limit:
            prefix = get_prefix(LogLevel.CRITICAL)
            msg = "Repeated unexpected shutdowns detected. Crash limit exceeded. Server restart attempts halted until manual intervention."
            self.logger.log(prefix + msg)
            self.automation_output_broadcaster.publish(prefix, msg)
        else:
            prefix = get_prefix(LogLevel.INFO)
            msg = "Automatic restart triggered due to unexpected server shutdown."
            self.logger.log(prefix + msg)
            self.automation_output_broadcaster.publish(prefix, msg)
            self.runner.start()
    

    def _scheduled_restart(self):
        """Internal method to handle scheduled restarts."""
        while True:
            # Get current time and today's restart time
            now = datetime.now()
            restart_date = now.replace(hour=self.config.restart_time[0], minute=self.config.restart_time[1], second=0, microsecond=0)

            # If today's restart time has passed, schedule for tomorrow
            if now >= restart_date:
                restart_date += timedelta(days=1)

            # Calculate seconds until restart
            seconds_until_restart = (restart_date - now).total_seconds()

            prefix = get_prefix(LogLevel.INFO)
            line = f"Scheduled server restart in {int(seconds_until_restart // 60)} minutes."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Subtract RESTART_WARNING_MINUTES for the warning period
            restart_date = restart_date - timedelta(minutes=RESTART_WARNING_MINUTES)
            seconds_until_restart = (restart_date - now).total_seconds()

            sleep(seconds_until_restart)

            # Warn users about the restart
            prefix = get_prefix(LogLevel.INFO)
            line = f"Server will restart in {RESTART_WARNING_MINUTES} minutes. Please prepare to log out."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Sleep for the warning period
            sleep(RESTART_WARNING_MINUTES * 60)

            # Perform the restart
            
            prefix = get_prefix(LogLevel.INFO)
            line = "Performing scheduled server restart now."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            with self.runner.lock():
                if self.runner.is_running():
                    self.runner.stop()
                self.backup_world_offline()
                self.runner.start()


    def _prune_old_backups(self, backup_root: Path):
        """Internal method to delete old backups based on the backup duration setting."""
        cutoff_time = datetime.now() - timedelta(days=self.config.backup_duration_days)
        for backup in backup_root.iterdir():
            try:
                backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            except Exception as e:
            # TODO: Improve error message with exception details
                prefix = get_prefix(LogLevel.ERROR)
                line = f"Failed to get backup timestamp for backup {backup.name}: {e}"
                self.logger.log(prefix + line)
                self.automation_output_broadcaster.publish(prefix, line)
                continue
            if backup_time < cutoff_time:
                try:
                    if backup.is_dir():
                        shutil.rmtree(backup)
                    else:
                        backup.unlink()
                    prefix = get_prefix(LogLevel.INFO)
                    line = f"Deleted old backup: {backup.name}"
                    self.logger.log(prefix + line)
                    self.automation_output_broadcaster.publish(prefix, line)
                except Exception as e:
                    # TODO: Improve error message with exception details
                    prefix = get_prefix(LogLevel.ERROR)
                    line = f"Failed to delete old backup {backup.name}: {e}"
                    self.logger.log(prefix + line)
                    self.automation_output_broadcaster.publish(prefix, line)


    def backup_world_offline(self):
        """Perform a backup of the world when the server is offline."""
        # Use the runner's lock to ensure atomic operation
        with self.runner.lock():
            # Refuse to backup if the server is running
            if self.runner.is_running():
                prefix = get_prefix(LogLevel.ERROR)
                line = "Cannot perform offline backup while server is running."
                self.logger.log(prefix + line)
                self.automation_output_broadcaster.publish(prefix, line)
                return
            
            # Prepare paths to backup
            world_dir = Path(self.config.world_loc)
            backup_root = Path(self.config.backup_loc)
            backup_root.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime(BACKUP_TIMESTAMP_FORMAT)
            dest_dir = backups_root / f"offline_world_backup_{timestamp}"
            temp_dir = backup_root / f".tmp_world_backup_{timestamp}"

            prefix = get_prefix(LogLevel.INFO)
            line = f"Starting offline world backup to {dest_dir.name}"
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Copy the world directory to a temporary location first so incomplete backups are not stored
            try:
                shutil.copytree(world_dir, temp_dir)
                temp_dir.rename(dest_dir)
            except Exception as e:
                # Remove the temporary directory if the backup fails
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                # Log an error message if the backup fails
                prefix = get_prefix(LogLevel.ERROR)
                # TODO: Improve error message with exception details
                prefix = get_prefix(LogLevel.ERROR)
                line = f"Offline world backup failed: {e}"
                self.logger.log(prefix + line)
                self.automation_output_broadcaster.publish(prefix, line)
                return
            
            # Compress the backup directory
            # TODO: Add a config option for compression
            final_path = dest_dir
            try:
                shutil.make_archive(dest_dir.name, 'zip', root_dir=dest_dir)
                shutil.rmtree(dest_dir, ignore_errors=True)
                final_path = dest_dir.with_suffix('.zip')
            except Exception as e:
                # Remove the zip file if compression fails
                if final_path.exists():
                    final_path.unlink(missing_ok=True)
                # Log an error message if compression fails
                prefix = get_prefix(LogLevel.ERROR)
                line = f"Offline world backup compression failed: {e}"
                self.logger.log(prefix + line)
                self.automation_output_broadcaster.publish(prefix, line)
                return
            
            prefix = get_prefix(LogLevel.INFO)
            line = f"Successfully completed offline world backup: {final_path.name}"
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Prune old backups from the backup directory
            self._prune_old_backups(backup_root)

            # Return the final backup path for further processing if needed
            return final_path


    def backup_world_online(self):
        """Perform a backup of the world when the server is online."""
        # to be implemented
        pass


    def smart_backup(self):
        """Perform a backup of the world, choosing online or offline based on server state."""
        with self.runner.lock():
            if self.runner.is_running():
                self.backup_world_online()
            else:
                self.backup_world_offline()
