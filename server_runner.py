from output_broadcaster import LineBroadcaster, SignalBroadcaster
import subprocess
import threading
import queue


class ServerRunner:
    def __init__(self, config):
        """
        Initialize ServerRunner with a configuration object.
        Args:
            config (ServerConfig): The server configuration instance.
        """
        self.config = config
        self.executable_loc = config.executable_loc
        self.shutdown_timeout = config.shutdown_timeout
        self.process = None
        self.stdout_broadcaster = LineBroadcaster()
        self.unexpected_shutdown_broadcaster = SignalBroadcaster()
        self._stdout_thread = None
        self._expected_shutdown = False


    def start(self):
        """
        Start the Minecraft Bedrock server subprocess.
        Raises:
            RuntimeError: If the server is already running.
        """
        if self.process:
            raise RuntimeError("Server is already running")

        self._expected_shutdown = False

        # Start the server process
        self.process = subprocess.Popen(
            [self.executable_loc],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Start a thread to read stdout
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stdout_thread.start()


    def is_running(self):
        """
        Check if the server process is currently running.
        Returns:
            bool: True if running, False otherwise.
        """
        # Verify self.process exists and the process is still active (self.process.poll() returns None while running)
        return self.process and self.process.poll() is None


    def _read_stdout(self):
        """Internal method run in a separate thread to continuously read stdout lines from the server process and enqueue them for processing."""
        for line in self.process.stdout:
            self.stdout_broadcaster.publish(line.rstrip())
        self.process.stdout.close()
        # Clean up runner state after process exits
        self.process = None
        self._stdout_thread = None
        # If the shutdown was not expected, we alert all subscribers
        if not self._expected_shutdown:
            self.unexpected_shutdown_broadcaster.publish()


    def send_command(self, command):
        """
        Send a command string to the server's stdin.
        Args:
            command (str): Command string to send to the server.
        Raises:
            RuntimeError: If the server is not currently running.
        """
        if not self.is_running():
            raise RuntimeError("Server is not running")
        # Send a command to the server's stdin and immediately flush it
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()


    def get_output_line(self, timeout=None):
        """
        Retrieve the next line of output from the server stdout queue.
        Args:
            timeout (float or None): How long to wait for a line. None waits indefinitely, 0 for a non-blocking call.
        Returns:
            line (str or None): The next line from stdout, or None if the queue is empty.
        """
        try:
            return self.stdout_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        
    
    def stop(self):
        """
        Gracefully stop the server by sending a stop command and waiting for the process to exit within the configured shutdown timeout. Forces kill if unable to stop gracefully.
        Raises:
            RuntimeError: If the server is not currently running.
        """
        if not self.is_running():
            raise RuntimeError("Server is not running")
        # Indicate that this was a expected shutdown
        self._expected_shutdown = True
        # Attempt to close the process properly
        self.send_command("stop")
        try:
            # Wait for the process to exit gracefully
            self.process.wait(timeout=self.shutdown_timeout)
        except subprocess.TimeoutExpired:
            # If the process does not exit in time, kill it
            self.process.kill()
            self.process.wait()
        # Clean up
        self.process = None
        self._stdout_thread = None
    

    def restart(self):
        """
        Restart the server by stopping and then starting it.
        Raises:
            RuntimeError: If stopping or starting fails.
        """
        self.stop()
        self.start()
