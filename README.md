# Bedrock Server Manager

A robust Python toolkit to automate, configure, and manage your Minecraft Bedrock Server, featuring Discord integration, validation, and automation capabilities.

## Features

- **Configuration Validation**: Reads and validates all settings from `settings.toml`; missing or invalid entries are reported with clear, Unix-style error outputs[attached_file:48].
- **Discord Bot Integration**: Manage and monitor your server using Discord commands, supporting essential functions like start, stop, restart, save, and access to server info[attached_file:47].
- **Extensible Design**: Modular codebase designed for easy expansion (planned: server_runner.py and automation.py for direct server management and scheduled automation).

## Getting Started

### Prerequisites

- Python 3.11+
- Minecraft Bedrock Dedicated Server
- Discord bot token & admin user IDs (Optional)

### Installation

## Configuration

Edit `settings.toml` to specify settings. Every required value is validated at startup; invalid or missing settings will be listed as follows:

```
bedrock-server:
  executable_location: missing (required)
  log_location: path does not exist
  backup_duration: must be an integer
```

Refer to the generated sample for all possible options.

## Usage

- Start the Discord bot and interact using these commands:
- `!help` — List available commands
- `!start`, `!stop`, `!restart` — Server control
- `!save`, `!online`, etc. — See user and server status
- Only Discord admins can execute admin/owner commands.

## Error Handling

- All fatal errors return Unix-standard exit code `1` and print structured details for straightforward troubleshooting.
- Missing configuration file: sample will be generated, with clear instructions for editing.

## Contributing

Pull requests and feedback welcomed! Please file issues for support or feature requests.
