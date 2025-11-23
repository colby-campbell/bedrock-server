from server_config import ServerConfig
from server_runner import ServerRunner
from server_automation import ServerAutomation
from discord_bot import DiscordBot
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


def cleanup():
    """Cleanup function to ensure server and bot are shut down on exit."""
    print("bedrock-server:")
    if bot is not None:
        print("  main: stopping Discord bot before exit...")
        bot.discord_bot_stop()
    if runner.is_running():
        print("  main: stopping server before exit...")
        runner.stop()
    if automation.logger.running:
        print("  main: stopping logger before exit...")
        automation.logger.stop()
    print("  main: exited cleanly")


if __name__ == "__main__":
    # Get config info, create server runner and automation instances, and create the discord bot
    config = ServerConfig()
    runner = ServerRunner(config)
    automation = ServerAutomation(config, runner)  # Placeholder for ServerAutomation instance
    bot = None

    # Register cleanup with atexit for normal and exception-based exits
    atexit.register(cleanup)

    # Start the Discord bot if enabled in the config
    if config.discord_bot:
        bot = DiscordBot(config, runner, automation)
        # Start the discord bot in a separate thread
        bot_thread = threading.Thread(target=bot.discord_bot_start, daemon=True)
        bot_thread.start()

    # Start the command-line interface
    cli = CommandLineInterface(config, runner, automation, bot)  # Placeholder for Command-Line Interface instance

    # Start the server and CLI
    runner.start()
    automation.start()
    cli.start()
