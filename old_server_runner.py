from queue import Queue
import subprocess as sp
import atexit
import threading
from time import sleep
from shutil import copytree, rmtree
from datetime import datetime, timedelta
import pause
from glob import glob
from discord.ext import commands
import discord
from os import path, getcwdb

# Last updated July 1, 2022
# NOTES:
# I added the new coords command and also made it so the discord bot responds better to the commands. I still have to
# fix the problem with the script not being able to close as the discord bot won't shut off. You should probably
# research more about async functions and the whole await thing as I've got no idea how that works.

# To-Do List
# - Make is so the server can actually stop
# - Add whitelist function (maybe)

# VARIABLES! -----------------------------------------------------------------------------------------------------------
# Used to detect whether or not a crash has occurred
running = False
# Server process
process = None
# Stores that last 25 lines output by the server
last_outputs = []
# List that contains all found errors
errors = []
# List that contains all of the currently online players!
players = []
# This is a list of the functions that the server_thread needs to run!
tasks = Queue()

# Variables that are set by the settings .txt file
executable = None
log_loc = None
world_loc = None
backup_loc = None
backup_dur = None
restart_time = None
discord_bot = False
admins = []

# Threads
output_thread = None
# daily_thread
# input_thread
# server_thread (Runs the server)


# Functions!
def clean_line(all_txt, replace_txt):
    # Get rid of txt
    all_txt = all_txt.replace(replace_txt, "")
    # Get rid of any quotation marks
    all_txt = all_txt.replace("\"", "")
    all_txt = all_txt.replace("\'", "")
    # Strip away any whitespace on the edges
    all_txt = all_txt.strip()
    # Return the cleaned line
    return all_txt


# Takes all found errors and prints them to user
def error(lst):
    for item in lst:
        print("ERROR: " + item)
    input()
    exit()


# Name of the settings .txt file
settings = "settings.txt"

# settings .txt file path
settings_loc = getcwdb().decode("utf-8") + "\\" + settings

# Make sure the settings .txt file exists!
if not path.exists(settings_loc):
    error(["Missing the " + settings + " text file!"])

# Read the settings txt file
with open(settings_loc, "r") as f:
    # Loop through ever line in the file
    for line in f:

        # If the line is a comment, skip it
        if line.startswith("#"):
            continue

        # If the line has a variable, find the variable and use it!
        elif line.startswith("executable_location ="):
            line = clean_line(line, "executable_location =")
            executable = line

        elif line.startswith("log_location ="):
            line = clean_line(line, "log_location =")
            log_loc = line

        elif line.startswith("world_location ="):
            line = clean_line(line, "world_location =")
            world_loc = line

        elif line.startswith("backup_location ="):
            line = clean_line(line, "backup_location =")
            backup_loc = line

        elif line.startswith("backup_duration ="):
            line = clean_line(line, "backup_duration =")
            try:
                backup_dur = int(line)
            except ValueError:
                errors.append("backup_duration cannot contain non-integer numbers!")

        elif line.startswith("restart_time ="):
            line = clean_line(line, "restart_time =")
            if line:
                try:
                    nums = [int(num) for num in line.split(":")]
                    if len(nums) != 2 or nums[0] < 0 or nums[0] > 24 or nums[1] < 0 or nums[1] > 60:
                        errors.append("restart_time is not a valid time")
                    else:
                        restart_time = nums
                except ValueError:
                    errors.append("restart_time cannot contain non-integer numbers!")

        elif line.startswith("discord_bot ="):
            line = clean_line(line, "discord_bot =")
            if "enabled" in line.lower() or "true" in line.lower():
                discord_bot = True

        elif line.startswith("admin_list ="):
            line = clean_line(line, "admin_list =")
            admins = [name.strip() for name in line.split(",")]


# Check all variables and file paths to make sure they are valid!
if executable is None or not path.exists(executable):
    errors.append("The executable_location path is not valid!")

elif log_loc is None or not path.exists(log_loc):
    errors.append("The log_location path is not valid!")

elif world_loc is None or not path.exists(world_loc):
    errors.append("The world_location path is not valid!")

elif backup_loc is None or not path.exists(backup_loc):
    errors.append("The backup_location path is not valid!")

elif not backup_dur:
    errors.append("The backup_duration must be filled in!")

# If any errors are found, print them out to the user
if errors:
    error(errors)


# WHEN PROGRAM IS EXITED! ----------------------------------------------------------------------------------------------
# Forcefully stops the server
def force_stop():
    global running
    running = False
    sp.Popen.terminate(process)


# When the program is stopped, the cleanup function is ran, stopping the server.
atexit.register(force_stop)


# RANDOM FUNCTIONS! ----------------------------------------------------------------------------------------------------
# last_outputs has all time stamps removed.
def add_output(txt):
    if len(last_outputs) == 25:
        last_outputs.pop(0)
    # If the text has a timestamp, let's remove that
    if txt[0] == "[" and "INFO]" in txt:
        index = txt.index("INFO]") + 6
        txt = txt[index:]
    last_outputs.append(txt)


# Saves the console output to a .txt file in the log folder
def save_output(txt):
    file = datetime.now().strftime("SERVER LOG %Y-%m-%d.txt")
    with open(log_loc + "\\" + file, "a+") as f:
        f.write(txt + "\n")


# Prints text to the console and saves it to the log file
def sprint(*txt):
    output = time_stamp() + " " + " ".join(txt)
    print(output)
    save_output(output)


# Gives a time stamp in the same way the server does!
def time_stamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S:%f")[:-3] + " INFO]"


# Saves the world and returns an error if it encounters a problem (txt is used for naming the world)
def save_world(txt):
    try:
        save_loc = backup_loc + "\\" + txt + " " + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        copytree(world_loc, save_loc)
    except:
        return "Failed to save the world"


def delete_old_worlds():
    # This will give us all of the names of the worlds
    worlds = glob(backup_loc + "/*")
    worlds = [world.split("\\")[-1] for world in worlds]
    deleted_worlds = []
    # Loop through the worlds and find any that are older than the max
    for world in worlds:
        try:
            # Puts all of the numbers into a nice list!
            nums = world.replace(" ", "-").split("-")[-6:]
            # Gets rid of the leading 0's and then converts into a integer
            nums = [int(num) for num in nums]
            # Puts the world file's date into a datetime class variable
            world_date = datetime(nums[0], nums[1], nums[2], nums[3], nums[4], nums[5])
            world_date += timedelta(days=backup_dur)
            # Tests to see if the world date is over 10 days old! If so, delete it!
            if world_date < datetime.now():
                rmtree(backup_loc + "\\" + world)
                deleted_worlds.append(world)
        except:
            sprint("Encountered a problem while trying to read the backup world:", world)

    # Gives output to the player, telling them if any backup worlds were deleted
    if len(deleted_worlds) == 1:
        sprint("Deleting world:", deleted_worlds[0])
    elif len(deleted_worlds) > 1:
        sprint("Deleting worlds:", ", ".join(deleted_worlds))
    else:
        sprint("No backups worlds exceeded the backup duration")


# PLAYER'S ONLINE FUNCTION ---------------------------------------------------------------------------------------------
# If a player has joined or disconnected, the server records it!
def players_online(output):
    if "INFO] Player connected:" in output:
        # Little janky but just gives the index of the end of "Player connected:"
        index1 = output.index("Player connected:") + 17
        # Find the spot right after the username of the person who has just connected or disconnected!
        index2 = output.index(", xuid:")
        name = output[index1: index2].strip()
        players.append(name)

    elif "INFO] Player disconnected:" in output:
        # Same as above but + 20 as "disconnected" is a longer word
        index1 = output.index("Player disconnected:") + 20
        # Find the spot right after the username of the person who has just connected or disconnected!
        index2 = output.index(", xuid:")
        name = output[index1: index2].strip()
        if name in players:
            players.remove(name)
        else:
            sprint("ERROR: Tried removing \"" + name + "\" from the players list variable, but \"" + name + "\" was not found.")

# Example text of a player connecting and disconnecting
# [2022-06-05 18:25:23:563 INFO] Player connected: Colbablast8, xuid: 2535418461580695
# [2022-06-05 18:25:41:494 INFO] Player disconnected: Colbablast8, xuid: 2535418461580695


# READ SERVER OUTPUT! --------------------------------------------------------------------------------------------------
# Receives and prints info from the server and also detects if the server has crashed!
def read_output():
    global last_outputs
    global running
    for line in process.stdout:
        processed_line = line.rstrip()
        if processed_line[0] != "[":
            processed_line = f"{time_stamp()} {processed_line}"
        add_output(line.rstrip())
        save_output(processed_line)
        players_online(processed_line)
        print(processed_line)
    if running:
        sprint("The server has crashed! Attempting to restart")
        # Clear the list of players online!
        players.clear()
        force_stop()
        tasks.put(start)


# SUBPROCESS COMMANDS! -------------------------------------------------------------------------------------------------
# Starts the server
def start():
    global output_thread
    global running

    # Make sure that the output thread is not running! If the output_thread is None, skip as this is the first run
    if output_thread is not None:
        while output_thread.is_alive():
            # This will loop until the old output_thread is dead (This is so it doesn't incorrectly assume a crash has occurred)
            sleep(1)

    # Set running to true once the thread has stopped
    running = True

    # Finds and deletes any old backups
    delete_old_worlds()

    # Reset last_outputs
    last_outputs.clear()

    # Start server
    global process
    process = sp.Popen(executable, universal_newlines=True, text=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)

    # Start a new thread and read server output on that thread
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()


# Sends information to the sever
def send_stdin(txt):
    process.stdin.write(txt + "\n")
    process.stdin.flush()


# COMMANDS FUNCTIONS! --------------------------------------------------------------------------------------------------
# Checks if the command given is valid then routes it to the correct function relating to the command
def check_command(txt):
    if txt.lower().startswith("stop"):
        stop()

    elif txt.lower().startswith("restart"):
        return restart()

    elif txt.lower().startswith("save"):
        return save()

    elif txt.lower().startswith("difficulty"):
        return difficulty(txt.split()[1])

    elif txt.lower().startswith("online"):
        return check_online()

    elif txt.lower().startswith("coords"):
        return coordinates(txt.split([1]))

    # If it matched no commands, the function returns an error message
    else:
        if txt:
            return f"Unkown command: {txt}. Please check that the command exists you L."


# Stops the server - Returns if it was a forced restart (the server took longer than 1 minute to shut down)
def peaceful_stop():
    global running
    running = False
    # Clear the players online list!
    players.clear()
    send_stdin("stop")
    counter = 0
    while counter != 60:
        # If the server stops correctly within 60 seconds, start the server back up again
        if "Quit correctly" in last_outputs:
            return
        sleep(1)
        counter += 1
    # If the timer reaches 60 seconds, forcefully restart the server and send an error message
    force_stop()
    return "Server took too long to stop and was forcefully shut down"


# Stops the server then exits the code
def stop():
    msg = peaceful_stop()
    if msg:
        sprint(msg)
    exit()


# Restarts the server - Returns if it was a forced restart (the server took longer than 1 minute to shut down)
def restart():
    msg = peaceful_stop()
    start()
    return msg


def save():
    # Tell the server to prepare for a save
    send_stdin("save hold")
    # Check if the server is ready to save
    while True:
        send_stdin("save query")
        sleep(1)
        if "Data saved. Files are now ready to be copied." in last_outputs:
            break
    msg = save_world("COMMAND SAVE")
    # Resume the save
    send_stdin("save resume")
    # If an error occurred while saving, continue sending the error!
    if msg:
        return msg
    # If no error occurred, tell the user that the world was successfully saved!
    else:
        return "The server was successfully backed up."


# Changes the difficulty - Returns a error message if there is one
def difficulty(txt):
    if txt.startswith("p"):
        lvl = "peaceful"
    elif txt.startswith("e"):
        lvl = "easy"
    elif txt.startswith("n"):
        lvl = "normal"
    elif txt.startswith("h"):
        lvl = "hard"
    else:
        return f"{txt.upper()} is not a valid difficulty setting."
    # Sends the command to server
    send_stdin(f"difficulty {lvl}")
    return f"The difficulty has been set to {txt.upper()}."


# Checks who is online and returns the player list!
def check_online():
    # If there are no players online, just return this message immediately!
    if not players:
        return "No players are online!"

    # Go through every player and use a testfor command to make sure that they are actually online

    counter_runout = []  # A list that stores all players that the game could not use the testfor commamnd on!
    not_found = []  # A list that stores all players that the testfor command couldn't find (dead or not in the game)

    for player in players:
        # last_outputs must be cleared so "No targets matched selector" is not discovered from a previous loop
        last_outputs.clear()
        send_stdin("testfor " + player)
        counter = 0
        while counter != 8:
            # If the player was found, yay! Move on!
            if "Found " + player in last_outputs:
                break
            # Uh oh the player wasn't found in the game!
            elif "No targets matched selector" in last_outputs:
                not_found.append(player)
                break
            sleep(0.125)
            counter += 1
        if counter == 8: # MUST BE THE SAME NUMBER AS THE "while counter != #"
            counter_runout.append(player)

    # Now we start preparing the response!
    response = ""

    # Get the first part of the message saying how many players are online
    if len(players) == 1:
        response += "1 player is online:"
    else:
        response += str(len(players)) + " players are online:"

    # Add the players online to the list!
    for player in players:
        name = player
        if player in counter_runout:
            name += " (!)"
        elif player in not_found:
            name += " (?)"
        response += "\n" + name

    # If the testfor command did not find one or more of the players, display this message at the end of the message.
    if not_found:
        response += "\n(?): The player is either dead in game or not connected to the server."

    # If the counter ran out for any of the names, display this message at the end of the message.
    if counter_runout:
        response += "\n(!): An error has occurred, msg Colby for details."

    return response


# This will turn on or off the coordinates
def coordinates(txt):
    command = "gamerule showcoordinates "
    if txt.startswith("on") or txt.startswith("enabled"):
        command += "true"
    elif txt.startswith("off") or txt.startswith("disabled"):
        command += "false"
    else:
        return f"{txt.upper()} is not a valid option."
    send_stdin(command)
    # Send response back
    if txt.startswith("on") or txt.startswith("enabled"):
        return "Turned on the coordinates."
    elif txt.startswith("off") or txt.startswith("disabled"):
        return "Turned off the coordinates."


# DAILY AUTO RESTART & SAVE! -------------------------------------------------------------------------------------------
def daily_restart():
    while True:
        # Grabs current date and stores it in a list
        date = [int(item) for item in datetime.now().strftime("%Y %#m %#d %#H %#M").split()]

        # Sets the date the next restart will be on
        restart_date = datetime(date[0], date[1], date[2], restart_time[0], restart_time[1])

        # If the scheduled restart hour is past the current hour, add one day to the clock
        if date[3] > restart_time[0]:
            restart_date += timedelta(days=1)

        # If the scheduled restart hour is the current hour and the restart minutes is past the current minutes,
        # add one day to the clock
        elif date[3] == restart_time[0] and date[4] >= restart_time[1]:
            restart_date += timedelta(days=1)

        sprint("The next auto restart will be", restart_date.strftime("%A, %B %#d, at %#I:%M %p"))

        # Sets the pause until date 5 minutes before it restarts!
        restart_date = restart_date - timedelta(minutes=5)

        # Waits until the restart_date
        pause.until(restart_date)

        # Send a message that the server restarts in 5 minutes
        sprint("Server restarting in 5 minutes")
        send_stdin("say Restarting in 5 minutes")
        # Wait 4 minutes
        sleep(240)
        # Send a message that the server restarts in 1 minute
        sprint("Server restarting in 1 minute!")
        send_stdin("say Restarting in 1 minute!")
        # Wait 1 minute
        sleep(60)
        # Send a message saying that the server is restarting!
        send_stdin("say Restarting!")

        # Stop the server
        msg = peaceful_stop()
        if msg:
            sprint(msg)

        # Save the world
        msg = save_world("DAILY SAVE")
        if msg:
            sprint(msg)

        # Start the server
        tasks.put(start)


# SERVER CONSOLE INPUT! ------------------------------------------------------------------------------------------------
def console_input():
    while True:
        command = input()
        # If the command contained text, save it to the log file
        if command:
            save_output(f"{time_stamp()} Command sent: {command}")
        # If the input starts with an exclamation mark, send it as input to the server
        if command.startswith("!"):
            if command == "!stop":
                print("Please use \"stop\" to stop the server or \"restart\" to restart the server")
            else:
                send_stdin(command[1:])
        # Otherwise, check if the command exists and if so, execute it
        else:
            msg = check_command(command)
            if msg:
                sprint(msg)


# TASK QUEUE FUNCTION! -------------------------------------------------------------------------------------------------
def event_loop():
    while True:
        next_task = tasks.get()
        next_task()


# CODE STARTS! ---------------------------------------------------------------------------------------------------------
# Print if the discord bot is enabled or disabled and print the admins
if discord_bot:
    sprint("The discord bot is enabled!")
    sprint("Admins:", ", ".join(admins))
else:
    sprint("The discord bot is disabled!")

# Start the server running thread!
# Alright so this isn't that necessary I just did it I felt like it. This loop is responsible for running the start()
# function for other threads. I may need to add it to the restart() function as that also calls start() but I'm lazy rn
server_thread = threading.Thread(target=event_loop, daemon=True)
server_thread.start()

tasks.put(start)

# Only run the daily restart if the restart_time is filled in!
if restart_time is not None:
    daily_thread = threading.Thread(target=daily_restart, daemon=True)
    daily_thread.start()

# Input Loop    NOTE: I have no idea why I can't use a daemon thread on this thing, maybe fix try and fix it?
input_thread = threading.Thread(target=console_input)
input_thread.start()

# DISCORD BOT! ---------------------------------------------------------------------------------------------------------
if discord_bot:

    # Super secret token, don't steal!
    TOKEN = "OTM2NzYwNDczNjQ5NTY1NzY3.YfR4LQ.UIBt3Bfu_p_gir2FMRgDErJqOKg"

    # Creates the bot
    bot = commands.Bot(command_prefix="$", case_insensitive=True)
    # We are making our own custom help command instead of the regular janky one
    bot.remove_command("help")

    # I don't think this works
    async def bot_shutdown():
        await bot.close()


    @bot.command(name="help")
    async def help(ctx):
        # Create the embedded text
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title="Help"
        )

        # Help command description
        embed.add_field(
            name="$help",
            value="Shows this message!",
            inline=False
        )

        # Stop command description
        embed.add_field(
            name="$stop",
            value="Stops the server as well as the discord bot. **Can only be used by an admin.**",
            inline=False
        )

        # Restart command description
        embed.add_field(
            name="$restart",
            value="Restarts the server. **Can only be used by an admin.**",
            inline=False
        )

        # Save command description
        embed.add_field(
            name="$save",
            value="Saves while the server is still running. **Can only be used by an admin.**",
            inline=False
        )

        # Difficulty command description
        embed.add_field(
            name="$difficulty",
            value="Changes the difficulty between peaceful, easy, normal, and hard. **Can only be used by an admin.**",
            inline=False
        )

        # Coordinates command description
        embed.add_field(
            name="$coords",
            value="Enables or disables the coordinates. Accepted inputs are *on*, *enabled*, *off*, *disabled*. **Can only be used by an admin.**",
            inline=False
        )

        # God command description
        embed.add_field(
            name="$god",
            value="Allows access to the command-line of the server software. **Can only be used by the bot owner.**",
            inline=False
        )

        # Players online command description
        embed.add_field(
            name="$online",
            value="Returns who is currently on the server.",
            inline=False
        )


    @bot.command(name="stop")
    async def discord_stop(ctx):
        if str(ctx.message.author) in admins:
            await ctx.send("Shutting down both the server and the bot. Contact the server owner to restart the server software.")
            stop()
        else:
            await ctx.send("Only admins can stop the server.")


    @bot.command(name="restart")
    async def discord_restart(ctx):
        if str(ctx.message.author) in admins:
            await ctx.send("Restarting the server...")
            msg = restart()
            if msg:
                await ctx.send(msg)
            # Wait until the server successfully restarts and send a message!
            counter = 0
            while counter != 60:
                # If the server stops correctly within 60 seconds, start the server back up again
                if "Server started." in last_outputs:
                    break
                sleep(1)
                counter += 1
            if counter != 60:
                await ctx.send("The server has started.")
            else:
                await ctx.send("The server has yet to start, contact the server owner if the server does not start soon.")
        else:
            await ctx.send("Only admins can restart the server.")


    @bot.command(name="save")
    async def discord_save(ctx):
        if str(ctx.message.author) in admins:
            await ctx.send("Making a backup of the world...")
            msg = save()
            if msg:
                await ctx.send(msg)
        else:
            await ctx.send("Only admins can back up the server.")


    @bot.command(name="difficulty")
    async def discord_difficulty(ctx, lvl):
        if str(ctx.message.author) in admins:
            msg = difficulty(lvl)
            if msg:
                await ctx.send(msg)
        else:
            await ctx.send("Only admins can change the difficulty.")


    @bot.command(name="coords")
    async def discord_players_online(ctx, txt):
        if str(ctx.message.author) in admins:
            msg = coordinates(txt)
            if msg:
                await ctx.send(msg)
        else:
            await ctx.send("Only admins can enable or disable the coordinates.")


    @bot.command(name="online")
    async def discord_players_online(ctx):
        await ctx.send(check_online())


    # SHOULD RETURN WHAT COMMAND WAS SENT AND MAYBE WHAT THE SERVER SAID IN RESPONSE?
    @bot.command(name="god")
    @commands.is_owner()
    async def discord_server_command(ctx, *txt):
        command = " ".join(txt)
        if command.lower().strip() == "stop":
            await ctx.send("Please use the built in stop command.")
        else:
            await ctx.send("Command sent: " + command)
            send_stdin(command)
            # See if the server sends back a response!
            # Ok so I'm just gonna clear last_outputs and hope to god it wasn't being used for something critical lmao
            last_outputs.clear()
            counter = 0
            response = ""
            while counter != 5 or not response:
                for output in last_outputs:
                    if output != "Running AutoCompaction..." or output.startswith("Player connected:") or output.startswith("Player disconnected:"):
                        response = output
                        break
                sleep(1)
                counter += 1
            if response:
                await ctx.send("Response received: " + response)
            else:
                await ctx.send("No response was received.")


    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("Only the server owner can use this command.")

    bot.run(TOKEN)
