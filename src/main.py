import sys
from core import ServerConfig
from core import ServerRunner
from core import ServerAutomation
from bot import DiscordBot
from cli import CommandLineInterface
import threading
import atexit

"""
There is a hierarchy for these Classes:
ServerConfig - reads settings file
^
ServerRunner - takes ServerConfig info and runs the server
^
ServerAutonomation - takes ServerRunner and ServerConfig to manage automations
^
DiscordBot - takes ServerRunner, ServerConfig, and ServerAutomation to provide Discord interface
^
Command-Line Interface - takes ServerRunner, ServerConfig, ServerAutomation, and DiscordBot to provide CLI interface
"""

# This is a list of output messages to print on exit
output_message = ["bedrock-server:"]


def cleanup():
    """Cleanup function to ensure server and bot are shut down on exit."""
    if bot is not None:
        output_message.append("  main: stopping Discord bot before exit...")
        bot.discord_bot_stop()
    if runner.is_running():
        output_message.append("  main: stopping server before exit...")
        runner.stop()
    if automation.logger.running:
        output_message.append("  main: stopping logger before exit...")
        automation.logger.stop()
    output_message.append("  main: exited cleanly")
    # Print all output messages at once
    print("\n".join(output_message))


if __name__ == "__main__":
    # Get config info, create server runner and automation instances, and create the discord bot
    config = ServerConfig()
    runner = ServerRunner(config)
    automation = ServerAutomation(config, runner)  # Placeholder for ServerAutomation instance
    bot = None

    # Register cleanup with atexit for normal and exception-based exits
    atexit.register(cleanup)

    # Start the Discord bot if enabled in the config
    if config.discord_bot_enabled:
        bot = DiscordBot(config, runner, automation)
        # Start the discord bot in a separate thread
        bot_thread = threading.Thread(target=bot.discord_bot_start, daemon=True)
        bot_thread.start()

    # Start the command-line interface
    cli = CommandLineInterface(config, runner, automation, bot)  # Placeholder for Command-Line Interface instance

    # Start the server and CLI
    try:
        runner.start()
    except (FileNotFoundError, RuntimeError) as e:
        output_message.append(f"  ServerRunner: {e}")
        sys.exit(2)
    automation.start()
    cli.start()
