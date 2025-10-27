class OutputBroadcaster:
    """Class to broadcast server output to multiple subscribers."""
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        """Register a new subscriber to receive output."""
        self.subscribers.append(callback)

    def publish(self, line):
        """Send a line of output to all registered subscribers using their callback function."""
        for callback in self.subscribers:
            callback(line)
