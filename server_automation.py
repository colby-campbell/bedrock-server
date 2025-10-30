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
        # Subscribe to the output broadcaster
        self.runner.stdout_broadcaster.subscribe(self.handle_server_output)
        # Create logger if enabled
        self.logger = BufferedDailyLogger(self.config.log_loc)
    

    def handle_server_output(self, line):
        # Process server output lines for automation triggers
        self.logger.log(line)
