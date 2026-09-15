"""
readme_description_lookup.py

Parses a single YAML block embedded in an experiment's README file. That
block is the sole source of both the experiment's metadata (name,
description, author, version, and any additional pass-through fields such
as "path") and the description assignments for its simulations/datasets.

The README stays a normal, freely readable text/markdown file for humans.
Only a single fenced ```yaml ... ``` block within it is parsed by this
script. Expected structure of that block:

    name: <experiment name>
    description: <experiment description>
    author: [<author id>, <author id>, ...]
    version: <experiment version>
    path: <optional pass-through field, e.g. relative sdl path>
    ...                       # any other pass-through field
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

"folders", "extensions" and "folders_fallback" are reserved for dataset/
simulation descriptions; every other top-level key is treated as
experiment metadata and passed through into metadata.json.

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
DESCRIPTION_KEYS = {"folders", "extensions", "folders_fallback"}


def load_readme_yaml(readme_path: str) -> dict:
    """
    Reads the README file at readme_path and returns the parsed content of
    its first fenced ```yaml ... ``` block (raw dict, meta fields and
    description keys mixed together). Raises FileNotFoundError / ValueError
    if the README, the yaml block, or the parsed content is invalid - the
    README is now the only source of experiment metadata, so there is no
    generic fallback to silently continue with.
    """
    path = Path(readme_path)
    if not path.exists():
        raise FileNotFoundError(f"README not found: {readme_path}")

    text = path.read_text(encoding="utf-8")
    match = YAML_BLOCK_PATTERN.search(text)
    if not match:
        raise ValueError(f"No ```yaml block found in {readme_path}")

    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Could not parse yaml block in {readme_path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(
            f"yaml block in {readme_path} did not parse into a mapping "
            f"(got {type(data).__name__})"
        )

    return data


def extract_meta(data: dict) -> dict:
    """Everything in the yaml block except the reserved description keys is experiment metadata."""
    return {k: v for k, v in data.items() if k not in DESCRIPTION_KEYS}


def extract_descriptions(data: dict) -> dict:
    """The reserved description keys, defaulting missing ones to empty dicts."""
    return {
        "folders": data.get("folders", {}) or {},
        "extensions": data.get("extensions", {}) or {},
        "folders_fallback": data.get("folders_fallback", {}) or {},
    }


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

    if extension in descriptions["extensions"]:
        ext_desc, is_priority = _normalize_extension_entry(descriptions["extensions"][extension])
        if is_priority:
            return _apply_placeholder(ext_desc, top_level_name)

    if folder_name in descriptions["folders"]:
        return _apply_placeholder(descriptions["folders"][folder_name], top_level_name)

    if extension in descriptions["extensions"]:
        ext_desc, _ = _normalize_extension_entry(descriptions["extensions"][extension])
        return _apply_placeholder(ext_desc, top_level_name)

    if folder_name in descriptions["folders_fallback"]:
        return _apply_placeholder(descriptions["folders_fallback"][folder_name], top_level_name)

    return f"Description of {file_name}"