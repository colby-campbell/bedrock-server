import logging
from format_helper import process_line


class BroadcastHandler(logging.Handler):
    """Custom logging handler that broadcasts log messages to an OutputBroadcaster."""
    def __init__(self, broadcaster, logger):
        super().__init__()
        self.broadcaster = broadcaster
        self.logger = logger

    def emit(self, record):
        """Emit a log record by publishing it to the broadcaster."""
        msg = self.format(record)
        timestamp, text = process_line(msg)
        # Send the timestamp and the text to the CLI
        self.broadcaster.publish(timestamp, text)
        # Just combine the timestamp and the text and send it to the logger
        self.logger.log(timestamp + text)
