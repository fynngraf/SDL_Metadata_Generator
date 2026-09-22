"""
file_type_lookup.py

Determines the "file_type" (e.g. input, output, data_product) using two
persistent dictionaries (JSON files):

1. Path-keyword dictionary: checked first. If a keyword (e.g. "output")
   appears anywhere in the file's path, the corresponding file_type is
   used directly (e.g. ".../output/..." -> "output").
2. Extension dictionary: used as a fallback if no path keyword matched.

Exception: an extension entry can be marked with "override_path": true -
in that case, the extension's file_type always wins, even if a path
keyword would otherwise have matched. Useful when a specific file type
(e.g. .csv -> data_product) must never be reclassified just because it
happens to sit in a folder named "output" or "input".

If neither the path nor the extension yields a match, the user is asked
interactively whether to add the extension to the extension dictionary -
if confirmed, the entry is saved immediately and becomes known
automatically from then on (including future runs).
"""

import json
import logging
from pathlib import Path

DEFAULT_MAP_FILE = "file_type_map.json"
DEFAULT_PATH_MAP_FILE = "file_type_path_map.json"

logger = logging.getLogger(__name__)

# Initial seed values for the extension-based dictionary, used only to
# create the file if it doesn't exist yet. Can be extended at any time,
# either manually or interactively (see get_file_type below).
#
# Two accepted forms per entry:
#   "ext": "type"                                  (short form)
#   "ext": {"type": "type", "override_path": true}  (long form - always
#                                                     wins over a path match)
DEFAULT_TYPE_MAP = {
    "par": "input",
    "yaml": "input",
    "csv": "data_product",
    "xdmf": "output",
}

# Initial seed values for the path-keyword dictionary. Checked BEFORE the
# extension dictionary: if any of these keys appears anywhere in the file's
# path, the corresponding file_type is used directly. Can be extended at
# any time by editing the JSON file manually.
DEFAULT_PATH_TYPE_MAP = {
    "output": "output",
    "input": "input",
}


def load_type_map(map_file: str = DEFAULT_MAP_FILE) -> dict:
    path = Path(map_file)
    if not path.exists():
        # On the very first call: create the file with the initial seed
        # values, so the dictionary lives exclusively in the JSON file
        # from now on (not just in memory for this run).
        initial_map = dict(DEFAULT_TYPE_MAP)
        save_type_map(initial_map, map_file)
        return initial_map
    with open(path, "r") as f:
        return json.load(f)


def save_type_map(type_map: dict, map_file: str = DEFAULT_MAP_FILE) -> None:
    path = Path(map_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(type_map, f, indent=4, sort_keys=True)
        f.write("\n")


def load_path_type_map(map_file: str = DEFAULT_PATH_MAP_FILE) -> dict:
    path = Path(map_file)
    if not path.exists():
        initial_map = dict(DEFAULT_PATH_TYPE_MAP)
        save_path_type_map(initial_map, map_file)
        return initial_map
    with open(path, "r") as f:
        return json.load(f)


def save_path_type_map(path_type_map: dict, map_file: str = DEFAULT_PATH_MAP_FILE) -> None:
    path = Path(map_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(path_type_map, f, indent=4, sort_keys=True)
        f.write("\n")


def _normalize_type_entry(entry) -> tuple[str, bool]:
    """
    Normalizes a file_type_map entry into (type_value, override_path).
    Accepts both the short form (plain string, override_path=False) and
    the long form ({"type": ..., "override_path": true/false}).
    """
    if isinstance(entry, dict):
        return entry.get("type", ""), bool(entry.get("override_path", False))
    return entry, False


def get_file_type_by_path(item_path: str, path_type_map: dict) -> str | None:
    """
    Checks whether any keyword from path_type_map appears anywhere in
    item_path (case-insensitive substring match). Returns the first
    matching file_type, or None if no keyword matches.

    IMPORTANT: item_path should be the FOLDER path only (excluding the
    file name itself) - e.g. ".../J1/output", not ".../J1/output/result.par".
    Otherwise a keyword could accidentally match against part of the file
    name (e.g. a file literally named "..._fault_...yaml" would wrongly
    match a "fault" keyword even though it doesn't actually live in a
    folder called "fault").

    Note: if multiple keywords match, the one that comes first when
    iterating the dictionary wins - keep the path-keyword dictionary free
    of ambiguous/overlapping keywords to avoid relying on this order.
    """
    path_lower = item_path.lower()
    for keyword, file_type in path_type_map.items():
        if keyword.lower() in path_lower:
            return file_type
    return None


def get_file_type(
    file_name: str,
    item_path: str | None = None,
    map_file: str = DEFAULT_MAP_FILE,
    type_map: dict | None = None,
    path_map_file: str = DEFAULT_PATH_MAP_FILE,
    path_type_map: dict | None = None,
) -> str:
    """
    Returns the file_type for a file, checked in this order:

    0. Extension dictionary, but ONLY if that extension is marked with
       "override_path": true - in that case it wins immediately, even
       over a matching path keyword.
    1. Path keywords (if item_path is given): e.g. "output" anywhere in
       the file's FOLDER path -> "output". item_path should be the folder
       path only, excluding the file name itself (see get_file_type_by_path
       for why). No interactive prompt if nothing matches here, since most
       paths simply won't contain any of the configured keywords.
    2. Extension dictionary (normal, non-override case): e.g. ".par" -> "input".
       If the extension is not found at all, the user is asked
       interactively (via console) whether to add it; if confirmed, it is
       saved immediately to map_file.

    type_map / path_type_map can optionally be passed in to handle
    multiple calls within a single session without repeatedly reloading
    the files - newly added entries then immediately apply to subsequent
    files within the same run.
    """
    owns_type_map = type_map is None
    if owns_type_map:
        type_map = load_type_map(map_file)

    if path_type_map is None:
        path_type_map = load_path_type_map(path_map_file)

    extension = file_name.split(".")[-1].lower()

    # 0. Extension override - checked first, on purpose, before the path.
    # Logged at debug level (--debug) so it's traceable which rule
    # decided the file_type (helpful when several people maintain the
    # same shared file_type_map.json).
    if extension in type_map:
        ext_value, ext_override = _normalize_type_entry(type_map[extension])
        if ext_override:
            logger.debug(f"'.{extension}' has override_path=true -> using '{ext_value}' (ignoring path)")
            return ext_value

    # 1. Path keywords
    if item_path is not None:
        path_match = get_file_type_by_path(item_path, path_type_map)
        if path_match is not None:
            return path_match

    # 2. Extension dictionary (normal case, already loaded above)
    if extension in type_map:
        ext_value, _ = _normalize_type_entry(type_map[extension])
        return ext_value

    # Not found anywhere -> ask interactively
    logger.warning(f"Unknown file extension: '.{extension}' (file: {file_name})")
    answer = input(f"Add '.{extension}' to the file_type dictionary? [y/n]: ").strip().lower()

    if answer in ("y", "yes", "j", "ja"):
        value = input(f"Which file_type should be set for '.{extension}'? (e.g. input, output, data_product): ").strip()
        type_map[extension] = value
        save_type_map(type_map, map_file)
        logger.info(f"'.{extension}' -> '{value}' has been saved to {map_file}")
        return value

    # Declined: one-off fallback without saving
    fallback = "output"
    logger.warning(f"Not saved. Using one-off fallback: '{fallback}'")
    return fallback
