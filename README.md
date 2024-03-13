# DirectorySync
A script to update a directory from one location to match that of another in a different location.
This will delete directories and files that are in `dest` and not in `src`, copy those in `src` and not in `dest`, and replace a file in `dest` if the two versions differ in size or if the `src` modification time is more recent.

## Python Run Command
`python <path_to_script> <src_directory> <destination_directory> [OPTIONS]`
## Options
* `-y`, `--skip-confirmation`: Skips the user path direction confirmation prompt.
* `--ll,` `--log-level`: set the log level
  * DEBUG
  * INFO
  * WARN
  * ERROR
  * FATAL

The program writes a log file into the directory it is run from. Multiple runs from the same directory appends to the same log file.

