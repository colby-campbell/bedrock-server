from prompt_toolkit import prompt, print_formatted_text, ANSI
from prompt_toolkit.patch_stdout import patch_stdout
from queue import Queue
from datetime import datetime
import re


def get_timestamp():
    """Get the current timestamp in the format YYYY-MM-DD HH:MM:SS:MMM"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f":{datetime.now().microsecond // 1000:03d}"


def process_line(line):
    """Process a line from the server."""
    pattern = re.compile(r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}:\d{3}) (?P<level>\w+)\](?: (?P<message>.*))?")
    match = pattern.match(line)
    if match:
        timestamp = match.group("timestamp")
        level = match.group("level")
        match level:
            case "INFO":
                ansi_code = "\033[34m"
            case "ERROR":
                ansi_code = "\033[31m"
            case _:
                ansi_code = "\033[33m"
        spacing = " " * (8 - len(level))
        message = match.group("message") or ""

        # Now you can format and print or log
        return f"\033[1;90m{timestamp} {ansi_code}{level}\033[0m{spacing}{message}"
    else:
        return f"\033[1;90m{get_timestamp()} \033[33mUNK\033[0m     {line}"


def add_timestamp(line):
    """Add a timestamp to a line."""
    return f"\033[1;90m{get_timestamp()} \033[35mCLI\033[0m     {line}"


class CommandLineInterface:
    """
    Command-Line Interface for interacting with the Minecraft Bedrock server.
    """

    BLOCKED_COMMANDS = {'stop', 'start', 'restart', 'exit', 'quit'}

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
            print_formatted_text(ANSI(process_line(line)))
        


    def start(self):
        """Start the command-line interface loop."""
        self.running = True
        # Print any queued output first
        while not self.outputQueue.empty():
            print("there was some queued ouptut!")
            print_formatted_text(ANSI(process_line(self.outputQueue.get())))
        # Main input loop
        while True:
            try:
                with patch_stdout():
                    input_text = prompt('bedrock-server> ').strip()
            except (EOFError, KeyboardInterrupt) as e:
                if not self.config.discord_bot or self.config.discord_bot and self.bot.bot.is_ready():
                    if isinstance(e, KeyboardInterrupt):
                        print(add_timestamp("KeyboardInterrupt received, forcefully exiting CLI..."))
                    else:
                        print(add_timestamp("EOF received, forcefully exiting CLI..."))
                    self.running = False
                    break
                else:
                    print_formatted_text(ANSI(add_timestamp("Cannot forcefully exit the CLI while the Discord bot is still starting.")))
                    continue
            # Process input
            if input_text.startswith(':'):
                # Process CLI built-in command
                cmd = input_text[1:].lower().strip()
                # Stop
                if cmd == 'stop':
                    if self.runner.is_running():
                        print_formatted_text(ANSI(add_timestamp("Stopping server...")))
                        self.runner.stop()
                    else:
                        print_formatted_text(ANSI(add_timestamp("Server is not running.")))
                # Start
                elif cmd == 'start':
                    if self.runner.is_running():
                        print_formatted_text(ANSI(add_timestamp("Server is already running.")))
                    else:
                        print_formatted_text(ANSI(add_timestamp("Starting server...")))
                        self.runner.start()
                # Restart
                elif cmd == 'restart':
                    if self.runner.is_running():
                        print_formatted_text(ANSI(add_timestamp("Restarting server...")))
                        self.runner.restart()
                    else:
                        print_formatted_text(ANSI(add_timestamp("Server is not running, starting server...")))
                        self.runner.start()
                # Exit
                elif cmd == 'exit' or cmd == 'quit':
                    if not self.config.discord_bot or self.config.discord_bot and self.bot.bot.is_ready():
                        if self.runner.is_running():
                            print_formatted_text(ANSI(add_timestamp("Stopping server before exit...")))
                            self.runner.stop()
                        print_formatted_text(ANSI(add_timestamp("Exiting CLI...")))
                        self.running = False
                        break
                    else:
                        print_formatted_text(ANSI(add_timestamp("Cannot exit the CLI while the Discord bot is still starting.")))
                else:
                    print_formatted_text(ANSI(add_timestamp(f"Unknown command '{cmd}'.")))
            else:
                # Block blocked commands without prefix
                words = input_text.lower().split()
                if words and words[0] in self.BLOCKED_COMMANDS:
                    print_formatted_text(ANSI(add_timestamp(f"Command '{words[0]}' is blocked. Use built-in CLI command ':{words[0]}' instead.")))
                # Otherwise send it as normal server input
                elif words and self.runner.is_running():
                    self.runner.send_command(input_text)
                else:
                    print_formatted_text(ANSI(add_timestamp("Server is not running, start the server to send commands.")))
