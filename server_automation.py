from buffered_daily_logger import BufferedDailyLogger
from datetime import datetime, timedelta
from output_broadcaster import LineBroadcaster
from format_helper import get_timestamp

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
    

    def handle_server_output(self, timestamp, line):
        # Process server output lines for automation triggers
        self.logger.log(timestamp + line)
    

    def handle_unexpected_shutdown(self, timestamp, line):
        self.logger.log(timestamp + line)
        self.automation_output_broadcaster.publish(timestamp, line)
        # Add the crash time to the list of crashes
        now = datetime.now()
        self.recent_crashes.append(now)
        # Get the timestamp for ten minutes ago
        ten_minutes_ago = now - timedelta(minutes=10)
        # If any of the timestamps are older than 10 minutes, remove them
        for time in self.recent_crashes:
            if time < ten_minutes_ago:
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