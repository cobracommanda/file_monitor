#!/usr/bin/env python
import sys
import time
import os
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set this flag to True if you want to perform the initial full copy.
PERFORM_INITIAL_COPY = False

def setup_logging(log_file):
    """
    Sets up logging with both a file handler and a console handler.
    Log messages include a timestamp, the log level, and the message.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

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
    def __init__(self, source_dir, output_dir, delay_time=0, debounce_delay=2):
        """
        delay_time: if > 0, the file copy will be delayed by that many seconds.
        debounce_delay: time in seconds to ignore subsequent events for the same file.
        """
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.delay_time = delay_time
        self.debounce_delay = debounce_delay
        # Dictionary to store the last processed timestamp per file.
        self.last_processed = {}

    def debounce_event(self, event):
        """
        Check if the event for the given file should be debounced.
        Returns True if the event should be ignored.
        """
        now = time.time()
        last_time = self.last_processed.get(event.src_path, 0)
        if now - last_time < self.debounce_delay:
            logging.info(f"Debouncing event for '{event.src_path}' (only {now - last_time:.2f} seconds since last event)")
            return True
        # Update the last processed time.
        self.last_processed[event.src_path] = now
        return False

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

    def handle_event_with_delay(self, event):
        """
        For events in the delayed pair, wait for the delay_time and then
        check the file modification time. If the file was modified more than
        delay_time seconds ago, skip the copy.
        """
        time.sleep(self.delay_time)
        try:
            mod_time = os.path.getmtime(event.src_path)
        except Exception as e:
            logging.error(f"Could not get modification time for '{event.src_path}': {e}")
            return

        # If the file was last modified more than delay_time seconds ago, skip copying.
        if (time.time() - mod_time) > self.delay_time:
            logging.info(f"Skipping copy of '{event.src_path}' because the modification time delay exceeded {self.delay_time} seconds")
            return

        self.copy_item(event.src_path)

    def on_created(self, event):
        if self.debounce_event(event):
            return

        if event.is_directory:
            logging.info(f"New directory detected: {event.src_path}")
            self.copy_item(event.src_path)
        else:
            logging.info(f"New file detected: {event.src_path}")
            if self.delay_time > 0:
                self.handle_event_with_delay(event)
            else:
                self.copy_item(event.src_path)

    def on_modified(self, event):
        if self.debounce_event(event):
            return

        if event.is_directory:
            logging.info(f"Modified directory detected: {event.src_path}")
            self.copy_item(event.src_path)
        else:
            logging.info(f"Modified file detected: {event.src_path}")
            if self.delay_time > 0:
                self.handle_event_with_delay(event)
            else:
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
    optionally performs an initial copy, and schedules a watcher to replicate file changes.
    For the pair with source:
      '/Volumes/BEC/CS Product English/Max_LIt_pours/xml_records/exported_xml/xml_v2/'
    a 10-second delayed copy is applied.
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

        # Optionally perform the initial copy.
        if PERFORM_INITIAL_COPY:
            logging.info(f"Performing initial copy for '{source_dir}'")
            initial_copy(source_dir, output_dir)

        # Determine if a delay is needed.
        # For the pair from xml_v2 to _TEST, we apply a 10-second delay.
        if os.path.normpath(source_dir) == os.path.normpath('/Volumes/BEC/CS Product English/Max_LIt_pours/xml_records/exported_xml/xml_v2/'):
            delay_time = 10
        else:
            delay_time = 0

        # Instantiate the event handler with our delay and debounce settings.
        event_handler = DirectoryWatcherHandler(source_dir, output_dir, delay_time=delay_time, debounce_delay=2)
        observer.schedule(event_handler, path=source_dir, recursive=True)
        logging.info(f"Watching directory: '{source_dir}' with output: '{output_dir}' (delay_time={delay_time}s, debounce_delay=2s)")

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
            ['/Users/DRobinson/Desktop/dev',
             '/Users/DRobinson/Desktop/dev 2'],
            ['/Users/DRobinson/Desktop/dev 2',
             '/Users/DRobinson/Desktop/dev']
        ]
    main(pairs)



