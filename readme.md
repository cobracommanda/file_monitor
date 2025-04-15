# Multi-directory Watcher with Logging

This repository contains a Python script that monitors one or more source directories for file system events—such as file creation, modification, or folder changes—and automatically copies the affected files and directories to corresponding output directories. The script uses the [watchdog](https://pypi.org/project/watchdog/) package to observe file system changes and logs all events to both the console and a log file (`directory_watcher.log`) in a professional, timestamped format.

## Features

- **Recursive Monitoring:** Watches the source directory and all its subdirectories.
- **Initial Copy:** Performs an initial copy of all files and folders from the source directory to the destination.
- **Multiple Folder Pairs:** Supports watching multiple source directories, each with its own designated output directory.
- **Robust Logging:** Logs all events (file copies, directory creation, errors, etc.) to both the console and a log file.
- **Error Handling:** Gracefully handles errors such as missing directories or permission issues.

## Requirements

- **Python 3.x**
- **Packages:**
  - `watchdog`

Install the required package using pip:

```bash
pip install watchdog
```
