import logging


class BroadcastHandler(logging.Handler):
    def __init__(self, broadcaster):
        super().__init__()
        self.broadcaster = broadcaster

    def emit(self, record):
        msg = self.format(record)
        self.broadcaster.publish(msg)
