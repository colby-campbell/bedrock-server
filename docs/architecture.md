# System Architecture

## Overview
This project consists of four main packages: `core`, `bot`, `cli`, and `utils`, each encapsulating a distinct part of the system’s functionality.

## Package Responsibilities
- **core**: Contains the server process management (`server_runner`), configuration (`server_config`), and automation (`server_automation`).
- **bot**: Manages the Discord bot integration allowing remote server control and notifications.
- **cli**: Provides a command-line interface subscribing to server output for local user interaction.
- **utils**: Helper modules including logging, formatting, and a broadcasting system.

## Dependency chain (bottom to top):
```
ServerConfig (reads settings.toml)
    ↓
ServerRunner (manages server process)
    ↓
ServerAutomation (scheduled tasks, crash detection)
    ↓
DiscordBot (Discord interface)
    ↓
CommandLineInterface (CLI with prompt_toolkit)
```

## Communication Patterns
- The project uses a publish-subscribe model using `output_broadcaster` to allow communication between lower-level components and higher-level components without tight coupling. This is implemented via `LineBroadcaster` and `SignalBroadcaster` classes in the `utils` package.

## Interaction and Flow
- The `main.py` script initializes and coordinates these components.
- `server_config` loads and validates configuration at startup.
- `server_runner` controls basic server operations and pushes output and unexpected shutdown signals through the broadcast system.
- `server_automation` subscribes to server output for logging, subscribes to unexpected shutdowns to trigger automated responses as well as re-publish them (explained later), and schedules tasks like restarts and backups.
- `discord_bot` listens for Discord commands and interacts with `server_runner` and `server_automation` to remotely control the server.
- `cli` subscribes to server output from `server_runner`, subscribes to unexpected shutdowns from `server_automation`, and provides a local interface for user commands.
- `utils` provides shared functionality like the broadcaster pattern for inter-component communication, daily logging, and output formatting.

## Thread Safety
- The `ServerRunner` class employs `threading.RLock()` to ensure thread-safe operations on the server process.
- The lock is also exposed via a context manager, allowing external components like `ServerAutomation` to perform multi-step operations atomically (e.g., stopping the server, performing a backup, and restarting the server) without race conditions.

## Deque-based Recent Lines Buffer
- `ServerAutomation` maintains a deque buffer of recent server output lines to monitor for specific events (e.g., save completion) during automated tasks. 
- Using a dequeue with a fixed maxiumum length ensures efficient memory usage while retaining the most relevant output for event detection.
- Every item is appened to the left side of the deque, ensuring the most recent lines are always at the front for quick access.