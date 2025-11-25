from utils import BufferedDailyLogger, LineBroadcaster, get_prefix, LogLevel
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep, strftime, time
import threading
import shutil
from collections import deque
import re

# Constants
RESTART_WARNING_MINUTES = 5
CRASH_DETECTION_WINDOW_MINUTES = 10
OFFLINE_BACKUP_PREFIX = "offline_world_backup"  # eg. "offline_world_backup_YYYY-MM-DD_HH-MM-SS"
ONLINE_BACKUP_PREFIX = "online_world_backup"    # eg. "online_world_backup_YYYY-MM-DD_HH-MM-SS"
TEMPORARY_BACKUP_PREFIX = ".tmp"                # eg. ".tmp_offline_world_backup_YYYY-MM-DD_HH-MM-SS"
PROTECTED_BACKUP_PREFIX = "protected"           # eg. "protected_offline_world_backup_YYYY-MM-DD_HH-MM-SS"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
DEQUE_MAX_LENGTH = 100
SUCCESS_PATTERN = r"Data saved. Files are now ready to be copied."
FAIL_PATTERN = r"A previous save has not been completed."
SAVE_QUERY_TIMEOUT_SECONDS = 10

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
        # Recent lines buffer for monitoring server output
        self._recent_lines = deque(maxlen=DEQUE_MAX_LENGTH)


    def log_print(self, level: LogLevel, line):
        """
        Logs and broadcasts a line with the given log level.
        Args:
            level (LogLevel): The log level of the message.
            line (str): The message to log and broadcast.
        """
        prefix = get_prefix(level)
        self.logger.log(prefix + line)
        self.automation_output_broadcaster.publish(prefix, line)


    def start(self):
        """Start the server automation tasks that require threads."""
        # Start the scheduled restart thread
        scheduled_restart_thread = threading.Thread(target=self._scheduled_restart, daemon=True)
        scheduled_restart_thread.start()
        # Prune old backups on startup
        self._prune_old_backups(Path(self.config.backup_loc))


    def handle_server_output(self, timestamp, line):
        """Process server output lines for automation triggers.
        Args:
            timestamp (str): The timestamp of the output line.
            line (str): The output line from the server.
        """
        self.logger.log(timestamp + line)
        self._recent_lines.appendleft(line)


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
            self.log_print(LogLevel.CRITICAL, "Repeated unexpected shutdowns detected. Crash limit exceeded. Server restart attempts halted until manual intervention.")
        else:
            self.log_print(LogLevel.INFO, "Automatic restart triggered due to unexpected server shutdown.")
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

            self.log_print(LogLevel.INFO, f"Scheduled server restart in {int(seconds_until_restart // 60)} minutes.")

            # Subtract RESTART_WARNING_MINUTES for the warning period
            restart_date = restart_date - timedelta(minutes=RESTART_WARNING_MINUTES)
            seconds_until_restart = (restart_date - now).total_seconds()

            sleep(seconds_until_restart)

            # Warn users about the restart
            self.log_print(LogLevel.INFO, f"Server will restart in {RESTART_WARNING_MINUTES} minutes. Please prepare to log out.")
            with self.runner.lock():
                if self.runner.is_running():
                    self.runner.send_command(f"say Server will restart in {RESTART_WARNING_MINUTES} minutes. Please prepare to log out.")

            # Sleep for the warning period
            sleep(RESTART_WARNING_MINUTES * 60)

            # Perform the restart
            self.log_print(LogLevel.INFO, "Performing scheduled server restart now.")

            with self.runner.lock():
                if self.runner.is_running():
                    self.runner.stop()
                self.backup_world_offline()
                self.runner.start()


    def _prune_old_backups(self, backup_root: Path):
        """Internal method to delete old backups based on the backup duration setting."""
        self.log_print(LogLevel.INFO, "Pruning old backups...")
        cutoff_time = datetime.now() - timedelta(days=self.config.backup_dur)
        pruned = []
        for backup in backup_root.iterdir():
            try:
                backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            except Exception as e:
            # TODO: Improve error message with exception details
                self.log_print(LogLevel.ERROR, f"Failed to get backup timestamp for backup {backup.name}: {e}")
                continue
            if backup_time < cutoff_time:
                # Skip protected backups, temporary backups, and only delete valid backups
                if backup.name.startswith(PROTECTED_BACKUP_PREFIX) or backup.name.startswith(TEMPORARY_BACKUP_PREFIX):
                    continue
                elif not (backup.name.startswith(OFFLINE_BACKUP_PREFIX) or backup.name.startswith(ONLINE_BACKUP_PREFIX)):
                    continue
                try:
                    if backup.is_dir():
                        shutil.rmtree(backup)
                    else:
                        backup.unlink()
                    pruned.append(backup.name)
                except Exception as e:
                    # TODO: Improve error message with exception details
                    self.log_print(LogLevel.ERROR, f"Failed to prune backup {backup.name}: {e}")
        if pruned:
            self.log_print(LogLevel.INFO, f"Pruned old backups: {', '.join(pruned)}")
        else:
            self.log_print(LogLevel.INFO, "No old backups to prune.")


    def backup_world_offline(self):
        """Perform a backup of the world when the server is offline."""
        # Use the runner's lock to ensure atomic operation
        with self.runner.lock():
            # Refuse to backup if the server is running
            if self.runner.is_running():
                self.log_print(LogLevel.ERROR, "Cannot perform offline backup while server is running.")
                return None
            
            # Prepare paths to backup
            world_dir = Path(self.config.world_loc)
            backup_root = Path(self.config.backup_loc)
            backup_root.mkdir(parents=True, exist_ok=True)

            timestamp = strftime(BACKUP_TIMESTAMP_FORMAT)
            dest_dir = backup_root / f"{OFFLINE_BACKUP_PREFIX}_{timestamp}"
            temp_dir = backup_root / f"{TEMPORARY_BACKUP_PREFIX}_{OFFLINE_BACKUP_PREFIX}_{timestamp}"

            self.log_print(LogLevel.INFO, f"Starting offline world backup to {dest_dir.name}")

            # Copy the world directory to a temporary location first so incomplete backups are not stored
            try:
                shutil.copytree(world_dir, temp_dir)
                temp_dir.rename(dest_dir)
            except Exception as e:
                # Remove the temporary directory if the backup fails
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                # Log an error message if the backup fails
                # TODO: Improve error message with exception details
                self.log_print(LogLevel.ERROR, f"Offline world backup failed: {e}")
                return None

            # Compress the backup directory
            # TODO: Add a config option for compression
            final_path = dest_dir
            # Optional compression flag ("compress_backups")
            if True:
                try:
                    # Compress the backup directory
                    shutil.make_archive(str(dest_dir), 'zip', root_dir=backup_root, base_dir=dest_dir.name)
                    # Remove the uncompressed backup directory
                    shutil.rmtree(dest_dir, ignore_errors=True)
                    final_path = dest_dir.with_suffix('.zip')
                except Exception as e:
                    self.log_print(LogLevel.WARN, f"Offline backup compression failed, keeping folder backup: {e}")

            self.log_print(LogLevel.INFO, f"Successfully completed offline world backup: {final_path.name}")

            # Prune old backups from the backup directory
            self._prune_old_backups(backup_root)

            # Return the final backup path for further processing if needed
            return final_path


    # TODO: should I give errors if something fails?
    def backup_world_online(self):
        """Perform a backup of the world while the server remains online.

        Protocol (Bedrock server commands):
        1. send 'save hold'   -> server begins holding world state for a consistent snapshot
        2. wait for confirmation output (best-effort pattern match)
        3. send 'save query'  -> server reports completion (optionally lists files; we rely on timing)
        4. copy world directory atomically (temp -> final -> optional compression)
        5. send 'save resume' -> release hold so server can continue normal writes

        Returns:
            Path | None: Final backup path if successful, else None.
        """
        # Use the runner's lock to ensure atomic operation
        with self.runner.lock():
            # Refuse to backup if the server is not running
            if not self.runner.is_running():
                self.log_print(LogLevel.ERROR, "Cannot perform online backup: server is not running.")
                return None

            # Prepare paths to backup
            world_dir = Path(self.config.world_loc)
            backup_root = Path(self.config.backup_loc)
            backup_root.mkdir(parents=True, exist_ok=True)

            timestamp = strftime(BACKUP_TIMESTAMP_FORMAT)
            dest_dir = backup_root / f"{ONLINE_BACKUP_PREFIX}_{timestamp}"
            temp_dir = backup_root / f"{TEMPORARY_BACKUP_PREFIX}_{ONLINE_BACKUP_PREFIX}_{timestamp}"

            self.log_print(LogLevel.INFO, f"Initiating online backup (hold/query) to {dest_dir.name}, expect ERROR messages indicating a previous save has not been completed.")

            # Step 1: save hold
            try:
                self.runner.send_command("save hold")
            except RuntimeError:
                self.log_print(LogLevel.ERROR, f"Failed to send 'save hold': server is not running.")
                return None

            # Step 2: save query
            hold_confirmed = False
            hold_deadline = time() + SAVE_QUERY_TIMEOUT_SECONDS
            success_index = -1
            while time() < hold_deadline and not hold_confirmed:
                # Run the save query command
                try:
                    self.runner.send_command("save query")
                except RuntimeError:
                    self.log_print(LogLevel.ERROR, f"Failed to send 'save query': server is not running.")
                    return None
                # Wait briefly for output to be processed to the deque buffer
                sleep(0.25)
                # Look through dequeue or a confirmation or failure pattern
                for index, line in enumerate(self._recent_lines):
                    if re.search(SUCCESS_PATTERN, line, re.IGNORECASE):
                        success_index = index
                        hold_confirmed = True
                    elif re.search(FAIL_PATTERN, line, re.IGNORECASE):
                        continue
            # If hold was not confirmed, log a warning
            if not hold_confirmed:
                self.log_print(LogLevel.WARN, "Save query failed; aborting backup.")
                try:
                    self.runner.send_command("save resume")
                except RuntimeError:
                    self.log_print(LogLevel.ERROR, "Save resume failed, server may still be in hold state.")
                return None

            # Extract file list from the output line preceding the success line
            files = []
            entries = self._recent_lines[success_index - 1].split(', ')
            for entry in entries:
                if ':' in entry:
                    path, size = entry.rsplit(':', 1)
                    files.append((path, int(size)))

            # Step 3: copy the necessary files to a temporary location
            self.log_print(LogLevel.INFO, "Copying necessary files for online backup...")
            try:
                # Copy each file reported by the save query
                for file_path, bytes in files:
                    # Create source and destination paths for each file
                    source = world_dir / file_path.replace(f"{world_dir.name}/", "")
                    dest = temp_dir / file_path.replace(f"{world_dir.name}/", "")
                    # Ensure the destination directory exists and copy the file
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    # Truncate the file to the requested size
                    f = open(dest, "a")
                    f.truncate(bytes)
                    f.close()
                # Rename the temporary directory to the final destination
                temp_dir.rename(dest_dir)
                # Resume server writes
                try:
                    self.runner.send_command("save resume")
                except RuntimeError:
                    self.log_print(LogLevel.ERROR, "Save resume failed, server may still be in hold state.")
            except Exception as e:
                # Remove the temporary directory if the backup fails
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                self.log_print(LogLevel.ERROR, f"Online world backup failed during copy: {e}")
                # Resume before returning
                try:
                    self.runner.send_command("save resume")
                except RuntimeError:
                    self.log_print(LogLevel.ERROR, "Save resume failed, server may still be in hold state.")
                return None

            # Step 4: Compress the backup directory
            # TODO: Add a config option for compression
            final_path = dest_dir
            # Optional compression flag ("compress_backups")
            if True:
                try:
                    # Compress the backup directory
                    shutil.make_archive(str(dest_dir), 'zip', root_dir=backup_root, base_dir=dest_dir.name)
                    # Remove the uncompressed backup directory
                    shutil.rmtree(dest_dir, ignore_errors=True)
                    final_path = dest_dir.with_suffix('.zip')
                except Exception as e:
                    self.log_print(LogLevel.WARN, f"Offline backup compression failed, keeping folder backup: {e}")

            self.log_print(LogLevel.INFO, f"Successfully completed online world backup: {final_path.name}")

            # Prune old backups
            self._prune_old_backups(backup_root)

            return final_path


    def smart_backup(self):
        """Perform a backup of the world, choosing online or offline based on server state."""
        with self.runner.lock():
            if self.runner.is_running():
                self.backup_world_online()
            else:
                self.backup_world_offline()
