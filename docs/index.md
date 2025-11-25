# Project Overview

This project is a Python automation system designed to manage a Minecraft Bedrock server efficiently. It integrates server automation, a Discord bot for remote control, and a command-line interface (CLI) for local management. This documentation provides an overview of the project's architecture, key features, and design goals.

## Origins

This project was created to streamline the management of a Minecraft Bedrock Dedicated Server. The goal was to automate routine tasks, provide remote control capabilities via Discord, and offer a user-friendly CLI for local server administration. Inspired by the same project I had worked on years ago, this new version is written with the best practices in mind, focusing on modularity, thread safety, and maintainability.

## Key Features

- **Server Automation:** Automated server startup, monitoring, and configuration management.
- **Discord Bot Integration:** Real-time server control and notifications via Discord.
- **Command-Line Interface (CLI):** Local commands for server status, control, and output monitoring.
- **Modular Architecture:** 
  - `core`: Contains the primary server logic and automation components.
  - `bot`: Handles the Discord bot integration.
  - `cli`: Manages the CLI functionality.
  - `utils`: General-purpose helper modules for logging, broadcasting, and formatting.

## Project Goals

- Create a maintainable, modular system for Minecraft server administration.
- Provide reliable remote and local server management interfaces.
- Maintain documentation to help with future development and contribution.
- Create a foundation for future enhancements, such as additional automation tasks or graphical interfaces.
