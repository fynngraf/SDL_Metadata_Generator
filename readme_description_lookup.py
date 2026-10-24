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
    filename_keywords:
      <keyword>: <description, optionally containing {folder}>
      ...

"folders", "extensions", "folders_fallback" and "filename_keywords" are
reserved for dataset/simulation descriptions; every other top-level key is
treated as experiment metadata and passed through into metadata.json.

Priority order:
1. "extensions" entries marked "priority: true" - always wins
2. "filename_keywords"   - keyword found as a token in the file name
                            (split on "_"/"-", matched case-insensitively),
                            checked in the order the keywords are listed -
                            the first one found wins
3. "folders"             - exact immediate parent folder name
4. "extensions"          - file extension (non-priority)
5. "folders_fallback"    - exact immediate parent folder name (second chance)
6. generic fallback description

"filename_keywords" exists for file names where the extension and folder
alone can't tell datasets apart, e.g. SeisSol output files that only differ
in a keyword placed right before the extension:
    run_normal-surface_cell.h5   -> "surface"  (not "cell")
    run_normal-fault_vertex.h5   -> "fault"    (not "vertex")
    run_normal_cell.h5           -> "cell"
List more specific keywords (e.g. "surface", "fault") before the generic
ones they can appear together with (e.g. "cell", "vertex") - list order is
priority order, since a file name can contain more than one keyword token.

The placeholder "{folder}" in a description is replaced with the top-level
folder name (e.g. "J1") if one is provided.
"""

import re
import yaml
from pathlib import Path

YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)
"""
Keys with dedicated handling elsewhere - excluded from extract_meta()'s 
generic pass-through so they don't leak into metadata.json as raw top-level 
fields. "coverage" is handled separately by coverage_lookup.py.

"""
DESCRIPTION_KEYS = {"folders", "extensions", "folders_fallback", "filename_keywords", "coverage"}

FILENAME_TOKEN_PATTERN = re.compile(r"[_-]")

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
        "filename_keywords": data.get("filename_keywords", {}) or {},
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


def _match_filename_keyword(filename_keywords: dict, file_name: str) -> str | None:
    """
    Splits file_name (without its extension) into tokens on "_"/"-" and
    checks filename_keywords in the order given - the first keyword found
    as an exact token (case-insensitive) wins. Returns None if none match.
    """
    stem = file_name.rsplit(".", 1)[0]
    tokens = {t.lower() for t in FILENAME_TOKEN_PATTERN.split(stem)}

    for keyword, description in filename_keywords.items():
        if keyword.lower() in tokens:
            return description
    return None


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
       (overrides everything else on purpose)
    1. descriptions["filename_keywords"]         (keyword token in the file name)
    2. descriptions["folders"][folder_name]      (exact immediate parent folder)
    3. descriptions["extensions"][".ext"]        (file extension, non-priority)
    4. descriptions["folders_fallback"][folder_name]
    5. generic fallback: "Description of <file_name>"
    """
    extension = "." + file_name.split(".")[-1].lower()

    if extension in descriptions["extensions"]:
        ext_desc, is_priority = _normalize_extension_entry(descriptions["extensions"][extension])
        if is_priority:
            return _apply_placeholder(ext_desc, top_level_name)

    keyword_desc = _match_filename_keyword(descriptions["filename_keywords"], file_name)
    if keyword_desc is not None:
        return _apply_placeholder(keyword_desc, top_level_name)

    if folder_name in descriptions["folders"]:
        return _apply_placeholder(descriptions["folders"][folder_name], top_level_name)

    if extension in descriptions["extensions"]:
        ext_desc, _ = _normalize_extension_entry(descriptions["extensions"][extension])
        return _apply_placeholder(ext_desc, top_level_name)

    if folder_name in descriptions["folders_fallback"]:
        return _apply_placeholder(descriptions["folders_fallback"][folder_name], top_level_name)

    return f"Description of {file_name}"