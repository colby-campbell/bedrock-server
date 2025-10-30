from buffered_daily_logger import BufferedDailyLogger

"""
This will need to manage server automation tasks like
- Scheduled restarts
- Automated Backups
    - Auto-delete old backups based on backup_duration setting
    - Notify users before backups/restarts
- Update checks (like for new versions of the server software)
- Logging
- Optional reboot on crash or extended server downtime
- Queue or buffer output?
"""


class ServerAutomation:
    def __init__(self, config, runner):
        self.config = config
        self.runner = runner
        # Subscribe to the stdout broadcaster and unexpected shutdown broadcaster
        self.runner.stdout_broadcaster.subscribe(self.handle_server_output)
        self.runner.unexpected_shutdown_broadcaster.subscribe(self.handle_unexpected_shutdown)
        # Create logger if enabled
        self.logger = BufferedDailyLogger(self.config.log_loc)
    

    def handle_server_output(self, timestamp, line):
        # Process server output lines for automation triggers
        self.logger.log(timestamp + line)
    

    def handle_unexpected_shutdown(self, timestamp, line):
        self.logger.log(timestamp + line)
