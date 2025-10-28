from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from queue import Queue


class CommandLineInterface:
    """
    Command-Line Interface for interacting with the Minecraft Bedrock server.
    """

    BLOCKED_COMMANDS = {'stop', 'start', 'restart'}

    def __init__(self, config, runner, automation, bot):
        """
        Initialize the Command-Line Interface with configuration, server runner, automation, and bot instances.
        Args:
            config (ServerConfig): The server configuration instance.
            runner (ServerRunner): The server runner instance.
            automation (ServerAutomation): The server automation instance.
            bot (DiscordBot): The Discord bot instance.
        """
        self.config = config
        self.runner = runner
        # Subscribe to the output broadcaster
        self.runner.broadcaster.subscribe(self.handle_server_output)
        self.automation = automation
        self.bot = bot
        # Stores the ouputs before the CLI is ready to display them
        self.outputQueue = Queue()
        self.running = True


    def handle_server_output(self, line):
        """Handle server output lines by printing them to the CLI."""
        if not self.running:
            self.outputQueue.put(line)
        else:
            print(line)


    def handle_input(self, input_text):
        input_text = input_text.strip()
        


    def start(self):
        """Start the command-line interface loop."""
        self.running = True
        # Print any queued output first
        while not self.outputQueue.empty():
            print("there was some queued ouptut!")
            print(self.outputQueue.get())
        # Main input loop
        while True:
            with patch_stdout():
                input_text = prompt('bedrock> ').strip()
            try:
                if input_text.startswith(':'):
                    # Process CLI built-in command
                    cmd = input_text[1:].lower().strip()
                    # Stop
                    if cmd == 'stop':
                        if self.server.is_running():
                            print("Stopping server...")
                            self.runner.stop()
                        else:
                            print("Server is not running.")
                    # Start
                    elif cmd == 'start':
                        if self.server.is_running():
                            print("Server is already running.")
                        else:
                            print("Starting server...")
                            self.runner.start()
                    # Restart
                    elif cmd == 'restart':
                        if self.server.is_running():
                            print("Restarting server...")
                            self.runner.restart()
                        else:
                            print("Server is not running. Starting server...")
                            self.runner.start()
                    else:
                        print(f"Unknown command: {cmd}")
                else:
                    # Block blocked commands without prefix
                    words = input_text.lower().split()
                    if words and words[0] in self.BLOCKED_COMMANDS:
                        print(f"Command '{words[0]}' is blocked. Use built-in CLI command ':{words[0]}' instead.")
                    # Otherwise send it as normal server input
                    elif words and self.runner.is_running():
                        self.runner.send_command(input_text)
                    else:
                        print("Server is not running. Start the server to send commands.")
            except (EOFError, KeyboardInterrupt) as e:
                if e is KeyboardInterrupt:
                    print("KeyboardInterrupt received, shutting down CLI...")
                else:
                    print("EOF received, shutting down CLI...")
                self.running = False
                break
