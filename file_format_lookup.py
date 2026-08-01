"""
file_format_lookup.py

Determines the "file_format" (e.g. PAR, XDMF, YAML) based on a file's
extension, using a persistent dictionary (JSON file). If an extension is
missing from the dictionary, the user is asked interactively whether to
add it - if confirmed, the entry is saved immediately and becomes known
automatically from then on (including future runs).
"""

import json
from pathlib import Path

DEFAULT_MAP_FILE = "file_format_map.json"

# Initial seed values, used only to create the file if it doesn't exist yet.
# Can be extended at any time, either manually or interactively (see
# get_file_format below).
DEFAULT_FORMAT_MAP = {
    "par": "PAR",
    "xdmf": "XDMF",
}


def load_format_map(map_file: str = DEFAULT_MAP_FILE) -> dict:
    path = Path(map_file)
    if not path.exists():
        # On the very first call: create the file with the initial seed
        # values, so the dictionary lives exclusively in the JSON file
        # from now on (not just in memory for this run).
        initial_map = dict(DEFAULT_FORMAT_MAP)
        save_format_map(initial_map, map_file)
        return initial_map
    with open(path, "r") as f:
        return json.load(f)


def save_format_map(format_map: dict, map_file: str = DEFAULT_MAP_FILE) -> None:
    path = Path(map_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(format_map, f, indent=4, sort_keys=True)
        f.write("\n")


def get_file_format(file_name: str, map_file: str = DEFAULT_MAP_FILE, format_map: dict | None = None) -> str:
    """
    Returns the file_format for a file based on its extension.
    If the extension is not found, the user is asked interactively
    (via console) whether to add it; if confirmed, it is saved
    immediately to map_file.

    format_map can optionally be passed in to handle multiple calls
    within a single session without repeatedly reloading the file -
    newly added entries then immediately apply to subsequent files
    within the same run.
    """
    owns_map = format_map is None
    if owns_map:
        format_map = load_format_map(map_file)

    extension = file_name.split(".")[-1].lower()

    if extension in format_map:
        return format_map[extension]

    # Not found -> ask interactively
    print(f"\nUnknown file extension: '.{extension}' (file: {file_name})")
    answer = input(f"Add '.{extension}' to the file_format dictionary? [y/n]: ").strip().lower()

    if answer in ("y", "yes", "j", "ja"):
        value = input(f"Which file_format should be set for '.{extension}'? (e.g. PAR): ").strip()
        format_map[extension] = value
        save_format_map(format_map, map_file)
        print(f"'.{extension}' -> '{value}' has been saved to {map_file}\n")
        return value

    # Declined: one-off fallback without saving (uppercased extension)
    fallback = extension.upper()
    print(f"Not saved. Using one-off fallback: '{fallback}'\n")
    return fallback
