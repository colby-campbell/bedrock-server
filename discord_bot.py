import asyncio

import discord
from discord.ext import commands

'''
DiscordBot module for managing a Minecraft Bedrock server via Discord commands.
'''


## Command to check if the user has admin privileges
def is_admin(admin_ids):
    async def predicate(ctx):
        # Check if the user is an admin or the bot owner
        is_owner = await commands.is_owner().predicate(ctx)
        is_admin = ctx.author.id in admin_ids
        return is_admin or is_owner

    return commands.check(predicate)


class DiscordBot:
    def __init__(self, config, server, automation):
        self.admin_list = config.admins
        self.token = config.bot_token
        self.server = server
        self.automation = automation
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    def discord_bot_start(self):
        # Create the help command
        @self.bot.command(name="help")
        async def discord_help(ctx):
            embed = discord.Embed(
                title="Help",
                description="Here's a list of all available commands.",
                color=discord.Color.red()
            )

            embed.add_field(
                name="Bot Owner Commands",
                value="\n".join([
                    "`!god` — Allows access to the command-line of the server software."
                ])
            )

            embed.add_field(
                name="Admin Commands",
                value="\n".join([
                    "`!stop` — Stop the server.",
                    "`!start` — Start the server.",
                    "`!restart` — Restart the server.",
                    "`!save` — Save the world while the server is still running.",
                    "`!check_for_update` — Checks for an update for the server software."
                    "`!difficulty` — Set the difficulty.",
                    "`!coords` — Set coordinates.",
                ]),
                inline=False
            )

            embed.add_field(
                name="General Commands",
                value="\n".join([
                    "`!help` — Show this message.",
                    "`!online` — Show who is online."
                ]),
                inline=False
            )

            await ctx.send(embed=embed)

        @commands.is_owner()
        @self.bot.command(name="god")
        async def discord_god(ctx):
            print("God command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="stop")
        async def discord_stop(ctx):
            print("Stop command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="start")
        async def discord_start(ctx):
            print("Start command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="restart")
        async def discord_restart(ctx):
            print("Restart command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="save")
        async def discord_save(ctx):
            print("Save command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="check_for_update")
        async def discord_check_for_update(ctx):
            print("Check for update command invoked")

        @is_admin(self.admin_list)
        @self.bot.command(name="difficulty")
        async def discord_difficulty(ctx):
            print("Difficulty command invoked")

        @self.bot.command(name="coords")
        async def discord_coords(ctx):
            print("Coords command invoked")

        @self.bot.command(name="online")
        async def discord_online(ctx):
            print("Online command invoked")

        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.errors.CheckFailure):
                await ctx.send("You do not have the permissions to use this command.")

        # Start the discord bot
        self.bot.run(self.token)

    def discord_bot_stop(self):
        # To shut down properly, schedule the close coroutine on the event loop
        asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
