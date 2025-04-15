#!/usr/bin/env python
import sys
import time
import os
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def setup_logging(log_file):
    """
    Sets up logging with both a file handler and a console handler.
    Log messages include a timestamp, the log level, and the message.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")

    # File handler writes to log file.
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler outputs to the console.
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class DirectoryWatcherHandler(FileSystemEventHandler):
    def __init__(self, source_dir, output_dir):
        self.source_dir = source_dir
        self.output_dir = output_dir

    def copy_item(self, src_path):
        # Get the relative path from the source directory.
        rel_path = os.path.relpath(src_path, self.source_dir)
        dest_path = os.path.join(self.output_dir, rel_path)

        if os.path.isdir(src_path):
            # If a directory, ensure it exists at the destination.
            if not os.path.exists(dest_path):
                try:
                    os.makedirs(dest_path, exist_ok=True)
                    logging.info(f"Created directory '{dest_path}'")
                except Exception as e:
                    logging.error(f"Error creating directory '{dest_path}': {e}")
        else:
            # For files, ensure the destination folder exists.
            dest_dir = os.path.dirname(dest_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.copy2(src_path, dest_path)
                logging.info(f"Copied '{src_path}' to '{dest_path}'")
            except Exception as e:
                logging.error(f"Error copying file '{src_path}': {e}")

    def on_created(self, event):
        if event.is_directory:
            logging.info(f"New directory detected: {event.src_path}")
        else:
            logging.info(f"New file detected: {event.src_path}")
        self.copy_item(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            logging.info(f"Modified directory detected: {event.src_path}")
        else:
            logging.info(f"Modified file detected: {event.src_path}")
        self.copy_item(event.src_path)


def initial_copy(source_dir, output_dir):
    """
    Walk through the source directory tree and copy each folder and file to
    the output directory while preserving the directory structure.
    """
    for dirpath, dirnames, filenames in os.walk(source_dir):
        for dirname in dirnames:
            src_dir_path = os.path.join(dirpath, dirname)
            dest_dir_path = os.path.join(output_dir, os.path.relpath(src_dir_path, source_dir))
            if not os.path.exists(dest_dir_path):
                try:
                    os.makedirs(dest_dir_path, exist_ok=True)
                    logging.info(f"Created directory '{dest_dir_path}'")
                except Exception as e:
                    logging.error(f"Error creating directory '{dest_dir_path}': {e}")
        for filename in filenames:
            src_file = os.path.join(dirpath, filename)
            dest_file = os.path.join(output_dir, os.path.relpath(src_file, source_dir))
            dest_file_dir = os.path.dirname(dest_file)
            if not os.path.exists(dest_file_dir):
                os.makedirs(dest_file_dir, exist_ok=True)
            try:
                shutil.copy2(src_file, dest_file)
                logging.info(f"Copied '{src_file}' to '{dest_file}'")
            except Exception as e:
                logging.error(f"Error copying file '{src_file}': {e}")


def main(pairs):
    """
    For each [source, destination] pair in pairs, validates the directories,
    performs an initial copy and schedules a watcher to replicate file changes.
    """
    setup_logging("directory_watcher.log")
    observer = Observer()

    for pair in pairs:
        # Clean up the provided directory strings.
        source_dir = pair[0].rstrip(',').strip()
        output_dir = pair[1].rstrip(',').strip()

        # Validate the source directory.
        if not os.path.exists(source_dir):
            logging.error(f"Source directory '{source_dir}' does not exist!")
            continue

        # Create the output directory if it doesn't exist.
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")

        logging.info(f"Performing initial copy for '{source_dir}'")
        initial_copy(source_dir, output_dir)

        # Schedule the event handler.
        event_handler = DirectoryWatcherHandler(source_dir, output_dir)
        observer.schedule(event_handler, path=source_dir, recursive=True)
        logging.info(f"Watching directory: '{source_dir}' with output: '{output_dir}'")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    # If command-line arguments are provided, they should be in multiples of 2:
    # [source1] [dest1] [source2] [dest2] ...
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        if len(args) % 2 != 0:
            print("Usage: python directory_watcher.py [source1] [dest1] [source2] [dest2] ...")
            sys.exit(1)
        pairs = []
        for i in range(0, len(args), 2):
            pairs.append([args[i], args[i + 1]])
    else:
        # Default configuration list if no command-line arguments are provided.
        pairs = [
            ['/Users/DRobinson/Desktop/untitled folder', '/Users/DRobinson/Desktop'],
            ['/Volumes/production/23 HTML eBooks/_BPS/mail_box/', '/Users/DRobinson/Desktop']
        ]
    main(pairs)
