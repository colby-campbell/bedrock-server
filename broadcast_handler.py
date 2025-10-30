import logging


class BroadcastHandler(logging.Handler):
    """Custom logging handler that broadcasts log messages to an OutputBroadcaster."""
    def __init__(self, broadcaster, logger):
        super().__init__()
        self.broadcaster = broadcaster
        self.logger = logger

    def emit(self, record):
        """Emit a log record by publishing it to the broadcaster."""
        msg = self.format(record)
        self.broadcaster.publish(msg)
        self.logger.log(msg)
