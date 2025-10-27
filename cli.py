from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
from queue import Queue


class CommandLineInterface:
    """
    Command-Line Interface for interacting with the Minecraft Bedrock server.
    """
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


    def start(self):
        """Start the command-line interface loop."""
        self.running = True
        # Print any queued output first
        while not self.outputQueue.empty():
            print(self.outputQueue.get())
        # Get 
        with patch_stdout():
            input_text = prompt('> ')  # User input stays clean
        
        if input_text.strip().lower() == "exit":
            if self.bot is not None:
                self.bot.discord_bot_stop()
            self.running = False
            return
        elif self.runner.is_running():
            # Send input to server stdin
            self.runner.process.send_command(input_text)
        else:
            print("Server is not running. Start the server to send commands.")
