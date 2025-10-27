from discord_bot import DiscordBot
from server_config import ServerConfig
import threading
import asyncio

'''
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
'''

# Get the configuration information and the create the discord bot
config = ServerConfig()
runner = None  # Placeholder for ServerRunner instance
automation = None  # Placeholder for ServerAutomation instance
client = DiscordBot(config.admins, runner, automation)

# Start the discord bot in a separate thread
bot_thread = threading.Thread(target=client.discord_bot_start, args=(config.bot_token,), daemon=True)
bot_thread.start()

try:
    while True:
        cmd = input("Type 'stop' to shut down the bot:\n")
        if cmd.strip().lower() == "stop":
            print("bedrock-server: shutting down discord bot")
            client.discord_bot_stop()
            break
except KeyboardInterrupt:
    print("bedrock-server: received keyboard interrupt, shutting down discord bot")
    client.discord_bot_stop()

# Wait for the bot thread to finish cleanly before exiting
bot_thread.join()
print("bedrock-server: discord bot has been shut down")