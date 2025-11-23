from buffered_daily_logger import BufferedDailyLogger
from datetime import datetime, timedelta
from output_broadcaster import LineBroadcaster
from format_helper import get_timestamp
from time import sleep
import threading

# Constants
RESTART_WARNING_MINUTES = 5
CRASH_DETECTION_WINDOW_MINUTES = 10

"""
This will need to manage server automation tasks like
- Scheduled restarts
- Automated Backups
    - Auto-delete old backups based on backup_duration setting
    - Notify users before backups/restarts
- Update checks (like for new versions of the server software)
- Logging (DONE!)
- Optional reboot on crash or extended server downtime
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
            prefix = get_timestamp() + " CRITICAL "
            msg = "Repeated unexpected shutdowns detected. Crash limit exceeded. Server restart attempts halted until manual intervention."
            self.logger.log(prefix + msg)
            self.automation_output_broadcaster.publish(prefix, msg)
        else:
            prefix = get_timestamp() + " INFO     "
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

            prefix = get_timestamp() + " INFO     "
            line = f"Scheduled server restart in {int(seconds_until_restart // 60)} minutes."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Subtract RESTART_WARNING_MINUTES for the warning period
            restart_date = restart_date - timedelta(minutes=RESTART_WARNING_MINUTES)
            seconds_until_restart = (restart_date - now).total_seconds()

            sleep(seconds_until_restart)

            # Warn users about the restart
            prefix = get_timestamp() + " INFO     "
            line = f"Server will restart in {RESTART_WARNING_MINUTES} minutes. Please prepare to log out."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            # Sleep for the warning period
            sleep(RESTART_WARNING_MINUTES * 60)

            # Perform the restart
            prefix = get_timestamp() + " INFO     "
            line = "Performing scheduled server restart now."
            self.logger.log(prefix + line)
            self.automation_output_broadcaster.publish(prefix, line)

            if self.runner.is_running():
                self.runner.restart()
            else:
                self.runner.start()
