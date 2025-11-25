# Design Decisions

## Why Python?

Python was chosen for its simplicity, readability, and extensive libraries. Its support for asynchronous programming is particularly beneficial for handling multiple tasks concurrently, such as managing server processes and responding to Discord events. Additionally, Python's cross-platform nature ensures that the automation system can run on various operating systems without significant modifications.

## Modular Package Structure
The project is divided into four main packages: `core`, `bot`, `cli`, and `utils`. This modular structure allows for clear separation of concerns:
- `core`: Manages the server process, configuration, and automation tasks.
- `bot`: Contains the Discord bot for remote server control.
- `cli`: Implements the command-line interface for local server management.
- `utils`: Provides shared utilities like logging, formatting, and broadcasting.

## Dependency Chain
The components are organized in a hierarchical dependency chain:
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
Each layer depends only on the layers below it, promoting low coupling and high cohesion. I chose this structure to help with adaptability and velocity in development. When adding new features, I can focus on the relevant layer without worrying about unintended side effects in higher layers.
