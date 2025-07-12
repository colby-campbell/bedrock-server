from discord_bot import DiscordBot
from config_reader import ServerConfig

config = ServerConfig()
client = DiscordBot(config.admins, None, None)
client.discord_bot_start(config.bot_token)

