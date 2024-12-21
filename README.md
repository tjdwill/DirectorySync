# DirectorySync

A script to update a directory from one location to match that of another with the same name in a
different location. This will delete directories and files that are in `dest` and not in `src`, copy
those in `src` and not in `dest`, and replace a file in `dest` if the two versions differ in size or
if the `src` modification time is more recent.

## Python Run Command

```bash
$ python <path_to_script> <src_directory> <destination_directory> [OPTIONS]
```

## Options
* `-m`. `--merge`: Keeps files that are unique to `dest` instead of deleting them.
* `-y`, `--skip-confirmation`: Skips the user path direction confirmation prompt.
* `--ll,` `--log-level`: set the log level
  * DEBUG
  * INFO
  * WARN
  * ERROR
  * FATAL

The program writes a log file into the directory it is run from. Multiple runs from the same
directory appends to the same log file.

