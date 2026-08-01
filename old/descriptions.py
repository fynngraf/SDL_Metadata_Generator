import json
import re
from pathlib import Path


def load_descriptions(templates_dir: str, exp_id: str) -> dict:
    desc_file = Path(templates_dir) / exp_id / "descriptions.json"

    if not desc_file.exists():
        print(f"Descriptions file does not exist: {desc_file} - use default")
        return {
            "file_extensions": {},
            "folders": {},
            "simulations": {},
            "datasets": {},
            "folder_files": {},
            "folder_extensions": {}
        }

    with open(desc_file, 'r') as f:
        descriptions = json.load(f)
        # Rückwärtskompatibilität: falls eine ältere descriptions.json ohne
        # "folder_files" / "folder_extensions" geladen wird, Schlüssel mit
        # leerem Dict ergänzen
        descriptions.setdefault("folder_files", {})
        descriptions.setdefault("folder_extensions", {})
        return descriptions


def sanitize_description(description: str) -> str:
    return description.replace('\n', ' ').replace('\r', ' ').replace('"', "'").strip()


def detect_numbered_simulation(simulation_name: str) -> str | None:
    match = re.search(r'(\D+?)(\d+)$', simulation_name)
    if match:
        prefix = match.group(1)   # z.B. "inputTW"
        number = match.group(2)   # z.B. "0001"
        return f"Simulation Run {number} for {prefix}"
    return None


def is_readme(file_name: str) -> bool:
    # case-insensitiver Vergleich, erkennt sowohl "README.txt" als auch "README" (ohne Endung)
    name_lower = file_name.lower()
    return name_lower == "readme.txt" or name_lower == "readme"


def get_file_format(descriptions: dict, file_name: str, folder_name: str) -> str:
    # Spezialfall: README-Dateien immer als "TXT" (unabhängig von Groß-/Kleinschreibung der Endung)
    if is_readme(file_name):
        return "TXT"

    file_ext = file_name.split(".")[-1]

    # Explizite Überschreibung über folder_extensions (Ordner + Endung)
    folder_ext_entry = get_folder_extension_entry(descriptions, file_ext, folder_name)
    if folder_ext_entry and "file_format" in folder_ext_entry:
        return folder_ext_entry["file_format"]

    # Explizite Überschreibung über file_extensions (global)
    if file_ext in descriptions.get("file_extensions", {}):
        entry = normalize_extension_entry(descriptions["file_extensions"][file_ext])
        if "file_format" in entry:
            return entry["file_format"]

    # Fallback: Dateiendung wie im Dateinamen (unverändert, wie bisher)
    return file_ext


def normalize_entry(entry) -> dict:
    # Kurzform (nur String) und Langform (Dict mit description/file_type) vereinheitlichen
    # Gilt für: datasets, folders, folder_files, simulations
    # (dort bedeutete ein reiner String schon immer "description")
    return entry if isinstance(entry, dict) else {"description": entry}


def normalize_extension_entry(entry) -> dict:
    # Kurzform (nur String) und Langform (Dict) vereinheitlichen
    # Gilt für: file_extensions, folder_extensions
    # WICHTIG: hier bedeutete ein reiner String schon immer "file_type"
    # (Rückwärtskompatibilität zu bestehenden descriptions.json-Dateien,
    # z.B. "file_extensions": {"par": "input"})
    return entry if isinstance(entry, dict) else {"file_type": entry}


def get_folder_file_entry(descriptions: dict, file_name: str, folder_name: str) -> dict | None:
    # spezifischste Zuweisung: exakte Kombination aus Ordner + Dateiname
    folder_entry = descriptions.get("folder_files", {}).get(folder_name)
    if folder_entry and file_name in folder_entry:
        return normalize_entry(folder_entry[file_name])
    return None


def get_folder_extension_entry(descriptions: dict, file_ext: str, folder_name: str) -> dict | None:
    # Zuweisung über Dateiendung, aber begrenzt auf einen bestimmten Ordner
    folder_entry = descriptions.get("folder_extensions", {}).get(folder_name)
    if folder_entry and file_ext in folder_entry:
        return normalize_extension_entry(folder_entry[file_ext])
    return None


def get_simulation_description(descriptions: dict, simulation_name: str) -> str:
    # 1. Einzelzuweisung in simulations (Kurzform "Text" oder Langform {"description": "Text", ...})
    if simulation_name in descriptions["simulations"]:
        entry = normalize_entry(descriptions["simulations"][simulation_name])
        if "description" in entry:
            return sanitize_description(entry["description"])

    # 2. Nummerierung erkannt
    numbered = detect_numbered_simulation(simulation_name)
    if numbered:
        return numbered

    # 3. Fallback
    return sanitize_description(f"Description of {simulation_name}")


def get_top_level_prefix(descriptions: dict, top_level_name: str | None) -> str | None:
    # Liefert die "simulations"-Beschreibung für den obersten Ordnernamen (z.B. "J1"),
    # falls dort ein Eintrag existiert - unabhängig von der Nummerierungs-Erkennung,
    # die get_simulation_description() zusätzlich beherrscht.
    if not top_level_name:
        return None
    if top_level_name in descriptions.get("simulations", {}):
        entry = normalize_entry(descriptions["simulations"][top_level_name])
        return entry.get("description")
    return None


def apply_placeholders(text: str, top_level_name: str | None) -> str:
    # Ersetzt "{top_level}" im Text durch den Namen des obersten Ordners (z.B. "J1"),
    # damit derselbe Beschreibungstext (z.B. bei file_extensions) für mehrere
    # Modellordner wiederverwendet werden kann.
    if top_level_name:
        return text.replace("{top_level}", top_level_name)
    return text


def get_dataset_description(descriptions: dict, file_name: str, folder_name: str,
                             top_level_name: str | None = None) -> str:
    file_ext = file_name.split(".")[-1]
    specific = None

    # 1. spezifischste Zuweisung: Ordner + Dateiname kombiniert
    folder_file_entry = get_folder_file_entry(descriptions, file_name, folder_name)
    if folder_file_entry and "description" in folder_file_entry:
        specific = folder_file_entry["description"]

    # 2. spezifische Datei (global, unabhängig vom Ordner)
    if specific is None and file_name in descriptions["datasets"]:
        entry = normalize_entry(descriptions["datasets"][file_name])
        if "description" in entry:
            specific = entry["description"]

    # 3. Dateiendung, aber begrenzt auf diesen Ordner
    if specific is None:
        folder_ext_entry = get_folder_extension_entry(descriptions, file_ext, folder_name)
        if folder_ext_entry and "description" in folder_ext_entry:
            specific = folder_ext_entry["description"]

    # 4. Ordner-Description (gilt für alle Dateien im Ordner)
    if specific is None and folder_name in descriptions["folders"]:
        entry = normalize_entry(descriptions["folders"][folder_name])
        if "description" in entry:
            specific = entry["description"]

    # 5. Dateiendung, global
    if specific is None and file_ext in descriptions["file_extensions"]:
        entry = normalize_extension_entry(descriptions["file_extensions"][file_ext])
        if "description" in entry:
            specific = entry["description"]

    if specific is not None:
        specific = apply_placeholders(specific, top_level_name)

    # Top-Level-Präfix (z.B. "Simulation output for rupture model J1 (...)")
    prefix = get_top_level_prefix(descriptions, top_level_name)
    if prefix:
        prefix = apply_placeholders(prefix, top_level_name)

    if prefix and specific:
        result = f"{prefix}: {specific}"
    elif prefix:
        result = prefix
    elif specific:
        result = specific
    else:
        result = "Unknown"

    return sanitize_description(result)


def get_file_type(descriptions: dict, file_name: str, folder_name: str, item_path: str) -> str:
    # 0. Spezialfall: README-Dateien immer als "input" (höchste Priorität)
    if is_readme(file_name):
        return "input"

    file_ext = file_name.split(".")[-1]

    # 1. spezifischste Zuweisung: Ordner + Dateiname kombiniert
    folder_file_entry = get_folder_file_entry(descriptions, file_name, folder_name)
    if folder_file_entry and "file_type" in folder_file_entry:
        return folder_file_entry["file_type"]

    # 2. Einzelzuweisung in datasets (global, unabhängig vom Ordner)
    if file_name in descriptions["datasets"]:
        entry = normalize_entry(descriptions["datasets"][file_name])
        if "file_type" in entry:
            return entry["file_type"]

    # 3. Dateiendung, aber begrenzt auf diesen Ordner
    folder_ext_entry = get_folder_extension_entry(descriptions, file_ext, folder_name)
    if folder_ext_entry and "file_type" in folder_ext_entry:
        return folder_ext_entry["file_type"]

    # 4. Ordnerzuweisung in folders
    if folder_name in descriptions["folders"]:
        entry = normalize_entry(descriptions["folders"][folder_name])
        if "file_type" in entry:
            return entry["file_type"]

    # 5. Dateityp in file_extensions (global)
    if file_ext in descriptions["file_extensions"]:
        entry = normalize_extension_entry(descriptions["file_extensions"][file_ext])
        if "file_type" in entry:
            return entry["file_type"]

    # 6. Fallback: "input" im Pfad
    if "input" in item_path.lower():
        return "input"

    return "output"
