class Broadcaster:
    """Class to broadcast server output to multiple subscribers."""
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        """
        Register a new subscriber to be called upon.
        Args:
            callback (func): Function to add to the subscribe list.
        """
        self.subscribers.append(callback)

class LineBroadcaster(Broadcaster):
    def publish(self, line):
        """
        Send a line of output to all registered subscribers using their callback function.
        Args:
            line (str): Line to send to all subscribers
        """
        for callback in self.subscribers:
            callback(line)

class SignalBroadcaster(Broadcaster):
    def publish(self):
        """Send an alert to all registered subscribers using their callback function."""
        for callback in self.subscribers:
            callback()

