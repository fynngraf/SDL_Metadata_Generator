"""
readme_description_lookup.py

Extracts "description" assignments from a YAML block embedded in an
experiment's README file, and provides lookup functions to determine the
description for a given folder (simulation) or file (dataset).

The README stays a normal, freely readable text/markdown file for humans.
Only a single fenced ```yaml ... ``` block within it is parsed by this
script. Expected structure of that block:

    folders:
      <folder_name>: <description, optionally containing {folder}>
      ...
    extensions:
      <.ext>: <description, optionally containing {folder}>
      # OR, to make this extension take precedence over "folders":
      <.ext>:
        description: <description, optionally containing {folder}>
        priority: true
      ...
    folders_fallback:
      <folder_name>: <description>
      ...

Normal priority (matches by exact folder name first, then file extension):
1. "folders"            - exact immediate parent folder name
2. "extensions"          - file extension
3. "folders_fallback"    - exact immediate parent folder name (second chance)
4. generic fallback description

Exception: if an "extensions" entry is written in the long form with
"priority: true", that extension's description wins even over a matching
"folders" entry - useful when a specific file type should always be
described the same way, regardless of which folder it happens to sit in.

The placeholder "{folder}" in a description is replaced with the top-level
folder name (e.g. "J1") if one is provided.
"""

import re
import yaml
from pathlib import Path

YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def load_readme_descriptions(readme_path: str) -> dict:
    """
    Reads the README file at readme_path, extracts the first fenced
    ```yaml ... ``` block, and parses it into a dict with the keys
    "folders", "extensions", "folders_fallback" (missing keys default to
    an empty dict).

    Prints a clear status message in every case, so it is always visible
    in the log whether descriptions were successfully loaded from the
    README, or whether generic fallback descriptions will be used instead
    (and why).
    """
    path = Path(readme_path)
    empty = {"folders": {}, "extensions": {}, "folders_fallback": {}}

    if not path.exists():
        print(f"[README] File not found: {readme_path} - using generic fallback descriptions")
        return empty

    text = path.read_text(encoding="utf-8")
    match = YAML_BLOCK_PATTERN.search(text)

    if not match:
        print(f"[README] No ```yaml block found in {readme_path} - using generic fallback descriptions")
        return empty

    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"[README] ERROR: Could not parse yaml block in {readme_path} - using generic fallback descriptions")
        print(f"[README]   Reason: {e}")
        return empty

    if not isinstance(data, dict):
        print(
            f"[README] ERROR: yaml block in {readme_path} did not parse into a mapping "
            f"(got {type(data).__name__}) - using generic fallback descriptions"
        )
        return empty

    data.setdefault("folders", {})
    data.setdefault("extensions", {})
    data.setdefault("folders_fallback", {})

    print(
        f"[README] Successfully loaded descriptions from {readme_path}: "
        f"{len(data['folders'])} folders, "
        f"{len(data['extensions'])} extensions, "
        f"{len(data['folders_fallback'])} folders_fallback entries"
    )
    return data


def _apply_placeholder(text: str, top_level_name: str | None) -> str:
    if top_level_name:
        return text.replace("{folder}", top_level_name)
    return text


def _normalize_extension_entry(entry) -> tuple[str, bool]:
    """
    Normalizes an "extensions" entry into (description_text, is_priority).
    Accepts both the short form (plain string, priority=False) and the
    long form ({"description": ..., "priority": true/false}).
    """
    if isinstance(entry, dict):
        return entry.get("description", ""), bool(entry.get("priority", False))
    return entry, False


def get_simulation_description(descriptions: dict, folder_name: str) -> str:
    """
    Description for a top-level folder itself (e.g. "J1" as a simulation).
    """
    if folder_name in descriptions["folders"]:
        return _apply_placeholder(descriptions["folders"][folder_name], folder_name)
    return f"Description of {folder_name}"


def get_dataset_description(
    descriptions: dict,
    file_name: str,
    folder_name: str,
    top_level_name: str | None = None,
) -> str:
    """
    Description for a file (dataset), checked in this order:
    0. descriptions["extensions"][".ext"] IF marked "priority: true"
       (overrides folders on purpose)
    1. descriptions["folders"][folder_name]      (exact immediate parent folder)
    2. descriptions["extensions"][".ext"]        (file extension, non-priority)
    3. descriptions["folders_fallback"][folder_name]
    4. generic fallback: "Description of <file_name>"
    """
    extension = "." + file_name.split(".")[-1].lower()

    # 0. Priority extension override - checked first, on purpose, before folders
    if extension in descriptions["extensions"]:
        ext_desc, is_priority = _normalize_extension_entry(descriptions["extensions"][extension])
        if is_priority:
            return _apply_placeholder(ext_desc, top_level_name)

    # 1. Folder match (normal case)
    if folder_name in descriptions["folders"]:
        return _apply_placeholder(descriptions["folders"][folder_name], top_level_name)

    # 2. Extension match (non-priority, already looked up above if present)
    if extension in descriptions["extensions"]:
        ext_desc, _ = _normalize_extension_entry(descriptions["extensions"][extension])
        return _apply_placeholder(ext_desc, top_level_name)

    # 3. Folder fallback
    if folder_name in descriptions["folders_fallback"]:
        return _apply_placeholder(descriptions["folders_fallback"][folder_name], top_level_name)

    # 4. Generic fallback
    return f"Description of {file_name}"
