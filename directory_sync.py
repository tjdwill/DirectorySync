# -*- coding: utf-8 -*-
"""
Created on Sat Oct 21 09:24:35 2023

@author: tjdwill
@revision: 12 March 2024
@description: Command-line tool to automate synchronization of two
same-named directories stored in different locations.
"""

import argparse
import logging
import os
import shutil
from pathlib import Path
from sys import exit


log_levels = {
    "DEBUG": logging.DEBUG, "INFO": logging.INFO,
    "WARN": logging.WARN, "ERROR": logging.ERROR,
    "FATAL": logging.FATAL
}
name_stem = "directory_sync.log"
log_name = str((Path() / name_stem).resolve())

# Argument Parsing Config
parser = argparse.ArgumentParser()
parser.add_argument(
    "source",
    help="The source path from which files will be copied."
)
parser.add_argument(
    "dest", 
    help=(
        "The destination path;"
        " the folder that will be updated."
    )
)
parser.add_argument(
    '-y', '--skip-confirmation',
    default=False,
    help="Run without FROM-TO directional confirmation.",
    action="store_true"
)
parser.add_argument(
    "--log-level", "--ll",
    help="Set the log file output level",
    type=str,
    choices=[
        *["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
    ],
    default="INFO",
)


# Function Defs

"""
Logic:
    - Start with the base folders.
    - Compare directory structures.
        - If dir or file in `dest` and not in `src`, delete it.
        - If dir or file in `src` and not in `dest`, copy it.
        - Otherwise, compare the size of the directories
            - If the same, do nothing
            - Else, add said path to the update list.
    - Once the first level comparison is done, iterate through the updated list
        - Run the same procedure as before.
"""

def dir_comp(
        src: Path,
        dest: Path,
        curr_list: list
) -> list:
    """
    Outputs an updated update_list

    Note: Due to the fact that calculating the size of a
    directory appears to involve traversing through it
    anyway, it makes sense to just traverse through the
    entire tree, so all subdirectories will be added
    to update_list.

    Parameters
    ----------
    src : Path
        Assumes an absolute path.
    dest : Path
        Destination path. Assumes absolute path.
    curr_list : list
        List of directories to traverse.

    Returns
    -------
    updated_list: list
        Updated list of directories to traverse.
    
    error_found: bool
        To inform user at end of program.
    """

    updated_list = curr_list
    error_found = False

    # At a given level, a directory's contents inherently form a set.
    src_items = {item.name for item in list(src.resolve().iterdir())}
    dest_items = {item.name for item in list(dest.resolve().iterdir())}

    src_unique = src_items.difference(dest_items)
    dest_unique = dest_items.difference(src_items)
    shared_items = src_items.intersection(dest_items)

    # Remove from dest all items not in src
    for item in dest_unique:
        path = dest / item
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                # Remove the file
                path.unlink()
        except PermissionError as e:
            logging.warning(f"Could not delete '{path}'.\n{e}")
            error_found = True
        else:
            logging.info(f"'{path}' Deleted.")

    # Copy unique items to dest
    for item in src_unique:
        path = src / item
        try:
            # Copy the entire directory if it doesn't exist in `dest`
            if path.is_dir():
                shutil.copytree(path, dest / item)
            else:
                # Copy the file
                shutil.copy2(path, dest / item)
        except PermissionError as e:
            logging.warning(f"Could not copy '{path}'.\n{e}")
            error_found = True
        else:
            logging.info(f"Copied {path} to {dest}.")

    # Iterate through the items that are in both paths
    for item in shared_items:
        src_path = src / item
        dest_path = dest / item

        src_item_stats = src_path.stat()
        dest_item_stats = dest_path.stat()

        if src_path.is_file():
            # Criteria: Either the file size has changed,
            # or the modification time.
            if (
                (src_item_stats.st_size != dest_item_stats.st_size) or
                (src_item_stats.st_mtime_ns > dest_item_stats.st_mtime_ns)
            ):
                try:
                    shutil.copy2(src_path, dest_path)
                except PermissionError as e:
                    logging.warning(f"Could not copy '{path}'.\n{e}")
                    error_found = True
                else:
                    logging.info(f"Copied {path} to {dest}.")
        elif src_path.is_dir():
            # Add to update list; adding to front of list
            # to iterate through subdirectories.
            updated_list.insert(0, src_path)
    else:
        updated_list.remove(src)
        return updated_list, error_found



if __name__ == '__main__':
    args = parser.parse_args()
    source_path, dest_path = args.source, args.dest
    log_lvl = args.log_level.upper()
    skip_confirmation = args.skip_confirmation

    src = Path(source_path).resolve()
    dest = Path(dest_path).resolve()

    # Initial Checks
    if not src.is_dir():
        print(f"[ERROR] Source folder: \"{src}\" is not a valid directory.\n")
        raise OSError
    if not dest.is_dir():
        print(f"[ERROR] Destination folder: \"{dest}\" is not a valid directory.\n")
        raise OSError
    if not (src.stem == dest.stem):
        print("Source and Destination directory names do not match.\n")
        print(f"Received stems:\n  Source: {src.stem}\n  Destination: {dest.stem}")
        raise ValueError
    if src.resolve() == dest.resolve():
        print("\nA path is always synced with itself.")
        exit()

    # Logging Configuration
    logging.basicConfig(
        filename=log_name,
        format="%(asctime)s %(levelname)s:%(message)s",
        datefmt='%d-%m-%Y %H:%M:%S',
        level=log_levels[log_lvl],
        encoding="utf-8"
    )
    print(f"Writing to file:\n{log_name}\n")
    
    # Ensure desired directionality
    confirmed = False
    while (not confirmed) and (not skip_confirmation):
        print(f'Folders to sync:\n  "FROM: {src}"\n  "TO: {dest}"\n')
        user_input = input("Files in destination folder may be deleted. Are you sure this the correct sync direction?  (y/n): ").lower()
        if user_input == 'y':
            confirmed = True
            continue
        elif user_input == 'n':
            print("Exiting Program.\n")
            exit()
        else:
            pass
    logging.info(f"\nDirectory Sync\nFROM: {src}\nTO: {dest}\nBegin.")

    # Begin Program
    update_list = [src]
    iter_src = src
    iter_dest = dest
    INFORM_USER = False

    done = False
    while not done:
        print(f'Traversing: "{iter_src}"')
        update_list, error_found = dir_comp(iter_src, iter_dest, update_list)
        if error_found:
            INFORM_USER = True
        if not update_list:
            done = True
            continue
        else:
            iter_src = update_list[0]
            next_path = os.path.relpath(iter_src, start=src)
            iter_dest = dest / next_path
    else:
        if INFORM_USER:
            print(
                "Some errors occurred during synchronization. "
                f"Check the log file:\n{log_name}\n"
            )
        print("\nSynchronization Complete.\n")
        logging.info("\nEnd.\n")
