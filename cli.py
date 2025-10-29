from prompt_toolkit import prompt, print_formatted_text, ANSI, PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from queue import Queue
from datetime import datetime
import re
import logging


def get_timestamp():
    """Get the current timestamp in the format YYYY-MM-DD HH:MM:SS:MMM"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f":{datetime.now().microsecond // 1000:03d}"


def process_line(line):
    """Process a line from the server."""
    # Detect and strip no log file prefix (this happens when the server is running two instances on the same port)
    if line.startswith("NO LOG FILE! - ["):
        line = line[len("NO LOG FILE! - "):]
        # Show a warning about this on first detection only once using getattr()
        if not getattr(process_line, "warned_no_log_file", False):
            print_formatted_text(ANSI(f"\033[1;90m{get_timestamp()} \033[33mWARNING\033[0m  Detected 'NO LOG FILE!' prefix in server output. This usually means another server instance is running or the log file is locked. Log output will only appear in the console and not in a file. Subsequent messages will not show this warning."))
            process_line.warned_no_log_file = True

    # Regex to parse log lines
    pattern = re.compile(r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:,]\d{3}) (?P<level>\w+)\](?: (?P<message>.*))?")
    match = pattern.match(line)
    if match:
        timestamp = match.group("timestamp")
        # Replace comma with colon in timestamp for consistency
        timestamp = timestamp.replace(",", ":")
        level = match.group("level")
        # ANSI color codes based on log level
        match level:
            case "RAW":
                ansi_code = "\033[32m"  # Green for raw
            case "DEBUG":
                ansi_code = "\033[36m"  # Cyan for debug
            case "INFO":
                ansi_code = "\033[34m"  # Blue for info
            case "WARNING":
                ansi_code = "\033[33m"  # Yellow for warning
            case "ERROR":
                ansi_code = "\033[31m"  # Red for error
            case "CRITICAL":
                ansi_code = "\033[1;31m"  # Bold red for critical
            case _:
                ansi_code = "\033[33m"  # Default to yellow for unrecognized levels
        # Calculate spacing for alignment
        spacing = " " * (max(9 - len(level), 1))
        # Get the message part ('or ""' to handle None case)
        message = match.group("message") or ""
        # Return the formatted line with ANSI codes
        return f"\033[1;90m{timestamp} {ansi_code}{level}\033[0m{spacing}{message}"
    else:
        # If the line doesn't contain a timestamp, return it with an 'RAW' level
        return f"\033[1;90m{get_timestamp()} \033[32mRAW\033[0m      {line}"


def add_timestamp(line):
    """Add a timestamp to a line for custom CLI responses."""
    return f"\033[1;90m{get_timestamp()} \033[35mCLI\033[0m      {line}"


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
        # Subscribe to the discord bot broadcaster if bot is provided
        if self.bot is not None:
            self.bot.broadcaster.subscribe(self.handle_discord_output)
        # TODO: Should I replace this with a unsubscribe?
        # Running variable so as to know when to stop printing to the screen
        self.running = True


    def handle_server_output(self, line):
        """Handle server output lines by printing them to the CLI."""
        if self.running:
            print_formatted_text(ANSI(process_line(line)))
    

    def handle_discord_output(self, line):
        """Print Discord log messages to the CLI with formatting."""
        if self.running:
            print_formatted_text(ANSI(process_line(line)))


    def start(self):
        """Start the command-line interface loop."""
        session = PromptSession()
        # Starting print messages for CLI
        print_formatted_text(ANSI(add_timestamp("Type ':help' for a list of built-in commands.")))
        print_formatted_text(ANSI(add_timestamp(f"Discord bot is {'ENABLED' if self.config.discord_bot else 'DISABLED'}")))
        # Main input loop
        while True:
            # Prompt for input
            try:
                with patch_stdout():
                    input_text = session.prompt('bedrock-server> ').strip()
            except (EOFError, KeyboardInterrupt) as e:
                # If the bot is not running or is fully started or fully stopped, allow exit
                if self.bot is None or self.bot is not None and self.bot.bot.is_ready() or self.bot is not None and self.bot.bot.is_closed():
                    if isinstance(e, KeyboardInterrupt):
                        print(add_timestamp("KeyboardInterrupt received, forcefully exiting CLI..."))
                    else:
                        print(add_timestamp("EOF received, forcefully exiting CLI..."))
                    self.running = False
                    break
                else:
                    print_formatted_text(ANSI(add_timestamp("Cannot forcefully exit the CLI while the Discord bot is still starting.")))
                    continue
            
            # Built-in CLI commands
            if input_text.startswith(':'):
                # Process CLI built-in command
                cmd = input_text[1:].lower().strip()
                # Help
                if cmd == 'help':
                    help_text = """
                    Built-in commands (prefix with ':'):
                    :help          Show this help message
                    :start         Start the Minecraft Bedrock server
                    :stop          Stop the server
                    :restart       Restart the server
                    :exit, :quit   Exit the CLI (and stop the server if running)
                    """
                    print_formatted_text(ANSI(add_timestamp(help_text.strip())))
                # Stop
                elif cmd == 'stop':
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
                    # If the bot is not running or is fully started or fully stopped, allow exit
                    if self.bot is None or self.bot is not None and self.bot.bot.is_ready() or self.bot is not None and self.bot.bot.is_closed():
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

            # Normal server command input
            else:
                # Block blocked CLI commands without prefix
                words = input_text.lower().split()
                if words and words[0] in self.BLOCKED_COMMANDS:
                    print_formatted_text(ANSI(add_timestamp(f"Command '{words[0]}' is blocked. Use built-in CLI command ':{words[0]}' instead.")))
                # Otherwise send it as normal server input
                elif words and self.runner.is_running():
                    self.runner.send_command(input_text)
                else:
                    print_formatted_text(ANSI(add_timestamp("Server is not running, start the server to send commands.")))
