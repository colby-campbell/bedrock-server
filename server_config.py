import tomllib
import os
import sys


'''
ServerConfig class that reads the config file and validates their variables.
'''


class ServerConfig:
    # The path to the config file
    CONFIG_PATH = "settings.toml"

    # A sample if no config exists
    SAMPLE_TOML = """\
    # Sample settings.toml — fill in real paths and values

    executable_location = "C:\\path\\to\\bedrock_server.exe"
    log_location        = "C:\\path\\to\\server.log"
    world_location      = "C:\\path\\to\\world"
    backup_location     = "C:\\path\\to\\backups"
    backup_duration     = 7
    shutdown_timeout    = 60
    restart_time        = "03:30"
    discord_bot         = true
    bot_token           = "bot token"
    admin_list          = [1234567890123456789]  # replace with your Discord IDs
    """

    def __init__(self):
        # Make sure a config file exists
        if not os.path.exists(self.CONFIG_PATH):
            with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(self.SAMPLE_TOML)
            print(f"bedrock-server: {self.CONFIG_PATH}: not found, sample created; edit it and rerun")
            sys.exit(1)

        # Load the config file
        with open(self.CONFIG_PATH, "rb") as f:
            cfg = tomllib.load(f)

        # TODO: Add default values for optional settings?
        # Load the config settings
        self.executable_loc = cfg.get("executable_location")
        self.log_loc = cfg.get("log_location")
        self.world_loc = cfg.get("world_location")
        self.backup_loc = cfg.get("backup_location")
        self.backup_dur = cfg.get("backup_duration")
        self.shutdown_timeout = cfg.get("shutdown_timeout")
        self.restart_time = cfg.get("restart_time")
        self.discord_bot = cfg.get("discord_bot")
        self.bot_token = cfg.get("bot_token")
        self.admins = cfg.get("admin_list")

        # Validate the config file settings
        errors = self.validate()
        if errors:
            print("bedrock-server:\n  " + "\n  ".join(errors))
            sys.exit(1)

    def validate(self):
        errors = []
        # executable_location
        if self.executable_loc is None:
            errors.append("executable_location: missing (required)")
        elif not isinstance(self.executable_loc, str):
            errors.append("executable_location: must be a string")
        elif not os.path.exists(self.executable_loc):
            errors.append("executable_location: path does not exist")
        # log_location
        if self.log_loc is None:
            errors.append("log_location: missing (required)")
        elif not isinstance(self.log_loc, str):
            errors.append("log_location: must be a string")
        elif not os.path.exists(self.log_loc):
            errors.append("log_location: path does not exist")
        # world_location
        if self.world_loc is None:
            errors.append("world_location: missing (required)")
        elif not isinstance(self.world_loc, str):
            errors.append("world_location: must be a string")
        elif not os.path.exists(self.world_loc):
            errors.append("world_location: path does not exist")
        # backup_location
        if self.backup_loc is None:
            errors.append("backup_location: missing (required)")
        elif not isinstance(self.backup_loc, str):
            errors.append("backup_location: must be a string")
        elif not os.path.exists(self.backup_loc):
            errors.append("backup_location: path does not exist")
        # backup_duration
        if self.backup_dur is None:
            errors.append("backup_duration: missing (required)")
        elif not isinstance(self.backup_dur, int):
            errors.append("backup_duration: must be an integer")
        # shutdown_timeout
        if self.shutdown_timeout is None:
            errors.append("shutdown_timeout: missing (required)")
        elif not isinstance(self.shutdown_timeout, int):
            errors.append("shutdown_timeout: must be an integer")
        # restart_time
        if self.restart_time is None:
            errors.append("restart_time: missing (required)")
        elif not isinstance(self.restart_time, str):
            errors.append("restart_time: must be a string in HH:MM format")
        else:
            try:
                # TODO: This could be done with regex?
                nums = [int(num) for num in self.restart_time.split(":")]
                if len(nums) != 2 or nums[0] < 0 or nums[0] > 24 or nums[1] < 0 or nums[1] > 60:
                    errors.append(f"restart_time: {self.restart_time}: invalid time")
                else:
                    self.restart_time = nums
            except ValueError:
                errors.append(f"restart_time: {self.restart_time}: cannot contain non-integer numbers")
        # discord_bot
        if not self.discord_bot:
            errors.append("discord_bot: missing (required)")
        if not isinstance(self.discord_bot, bool):
            errors.append("discord_bot: must be a boolean")
        # token
        if self.bot_token is None:
            errors.append("bot_token: missing (required)")
        elif not isinstance(self.bot_token, str):
            errors.append("bot_token: must be a string")
        # admin_list
        if not isinstance(self.admins, list):
            errors.append("admin_list: must be a list containing Discord ID's as integers")

        return errors
