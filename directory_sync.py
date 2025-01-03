#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 21 09:24:35 2023

@author: tjdwill
@revision: 20 December 2024
@description: Command-line tool to automate synchronization of two
same-named directories stored in different locations.
"""

import argparse
import logging
import os
import shutil
from pathlib import Path
from sys import exit


# Logging Configuration

log_levels = {
    "DEBUG": logging.DEBUG, "INFO": logging.INFO,
    "WARN": logging.WARN, "ERROR": logging.ERROR,
    "CRIT": logging.CRITICAL
}
name_stem = "directory_sync.log"
log_name = str((Path() / name_stem).resolve())
log = logging.getLogger('directory_sync')
log.setLevel(logging.DEBUG)

file_handle = logging.FileHandler(log_name, encoding="utf-8")
file_handle.setLevel(logging.DEBUG)

main_fmtr = logging.Formatter(
    fmt="%(asctime)s %(levelname)s:%(message)s",
    datefmt='%d-%m-%Y %H:%M:%S'
)
basic_fmt = logging.Formatter(fmt="%(asctime)s\n%(message)s", datefmt='%d-%m-%Y %H:%M:%S')

file_handle.setFormatter(basic_fmt)
log.addHandler(file_handle)


# Argument Parsing Config
parser = argparse.ArgumentParser(
    # prog="DirectorySync",
    description=(
        "A script to perform unidirectional synchronization between two "
        "directories of the same name stored in different places."
    )
)
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
    '-m', '--merge',
    default=False, 
    help="Keeps files that are unique to `dest` instead of deleting them.",
    action="store_true"
)
parser.add_argument(
     "-ll", "--log-level",
    help="Set the log file output level",
    type=str,
    choices=[
        *["DEBUG", "INFO", "WARN", "ERROR", "CRIT"]
    ],
    default="WARN",
)
parser.add_argument(
    '-y', '--skip-confirmation',
    default=False,
    help="Run without FROM-TO directional confirmation.",
    action="store_true"
)


# %% Function Defs

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
        curr_list: list,
        merge: bool
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
        The directory to sync with. At the end of a successful run, `dest` should match `src`.
        Assumes an absolute path.
    dest : Path
        Destination path. Assumes absolute path.
    curr_list : list
        List of directories to traverse.
    merge : bool
        Triggers merging behavior. When True, the program keeps files that are 
        in *dest* but not in *src* (instead of removing them).

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
    if not merge:
        for item in dest_unique:
            path = dest / item
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    # Remove the file
                    path.unlink()
            except PermissionError as e:
                log.warning(f"Could not delete '{path}'.\n{e}")
                error_found = True
            else:
                log.info(f"Deleted '{path}'.")

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
            log.warning(f"Could not copy '{path}'.\n{e}")
            error_found = True
        else:
            log.info(f"Copied {path} to {dest}.")

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
                    log.warning(f"Could not copy '{src_path}'.\n{e}")
                    error_found = True
                else:
                    log.info(f"Copied {src_path} to {dest_path}.")
        elif src_path.is_dir():
            # Add to update list; adding to front of list
            # to iterate through subdirectories.
            updated_list.insert(0, src_path)
    else:
        updated_list.remove(src)
        return updated_list, error_found



if __name__ == '__main__':

    # Parse Command-line
    args = parser.parse_args()
    SOURCE_PATH, DEST_PATH = args.source, args.dest
    LOG_LVL = args.log_level.upper()
    SKIP_CONFIRMATION = args.skip_confirmation
    MERGE = args.merge


    # Initial Checks
    src = Path(SOURCE_PATH).resolve()
    dest = Path(DEST_PATH).resolve()
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
    print(f"Writing to file:\n{log_name}\n")


    # Ensure desired directionality
    confirmed = False
    while (not confirmed) and (not SKIP_CONFIRMATION):
        print(f'Folders to sync:\n  "FROM: {src}"\n  "TO: {dest}"\n')
        user_input = input(
            "Files in destination folder may be deleted. "
            "Are you sure this the correct sync direction?  (y/n): "
        ).lower()
        if user_input == 'y':
            confirmed = True
            continue
        elif user_input == 'n':
            print("Exiting Program.\n")
            exit()
        else:
            pass


    # Begin Program
    log.info(f"Directory Sync\nFROM: {src}\nTO: {dest}\nBegin.")
    file_handle.setFormatter(main_fmtr)
    file_handle.setLevel(log_levels[LOG_LVL])

    INFORM_USER = False  # Was an error written to the log file?
    update_list = [src]
    iter_src = src
    iter_dest = dest
    done = False
    while not done:
        print(f'Traversing: "{iter_src}"')
        update_list, error_found = dir_comp(
            iter_src,
            iter_dest,
            update_list,
            MERGE,
        )
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

        file_handle.setFormatter(basic_fmt)
        file_handle.setLevel(logging.DEBUG)
        log.info("End.\n")
