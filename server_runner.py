import subprocess
import threading
import queue


class ServerRunner:
    def __init__(self, config):
        self.config = config
        self.executable_loc = config.executable_loc
        self.shutdown_timeout = config.shutdown_timeout
        self.process = None
        self.stdout_queue = queue.Queue()
        self._stdout_thread = None
    

    # Method to start the server process
    def start(self):
        if self.process:
            raise RuntimeError("Server is already running")
        
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


    # Method to check if the server is running
    def is_running(self):
        # Verify self.process exists and the process is still active (self.process.poll() returns None while running)
        return self.process and self.process.poll() is None


    # Private method to read stdout in a separate thread
    def _read_stdout(self):
        for line in self.process.stdout:
            self.stdout_queue.put(line)
        self.process.stdout.close()


    # Method to send a command to the server
    def send_command(self, command):
        if not self.is_running():
            raise RuntimeError("Server is not running")
        # Send a command to the server's stdin and immediately flush it
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()


    # Method to get a line of output from the server
    def get_output_line(self, timeout=None):
        try:
            return self.stdout_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        
    
    # Method to stop the server process
    def stop(self):
        if not self.is_running():
            raise RuntimeError("Server is not running")
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
        with self.stdout_queue.mutex:
            self.stdout_queue.queue.clear()
        self._stdout_thread = None
