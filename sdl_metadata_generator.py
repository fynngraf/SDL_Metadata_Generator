import argparse
import json
import logging
import os
#import numpy as np
from pathlib import Path
from file_format_lookup import get_file_format, load_format_map, DEFAULT_MAP_FILE as DEFAULT_FORMAT_MAP_FILE
from file_type_lookup import (
    get_file_type,
    load_type_map,
    load_path_type_map,
    DEFAULT_MAP_FILE as DEFAULT_TYPE_MAP_FILE,
    DEFAULT_PATH_MAP_FILE as DEFAULT_TYPE_PATH_MAP_FILE,
)
from readme_description_lookup import (
    load_readme_yaml,
    extract_meta,
    extract_descriptions,
    get_simulation_description,
    get_dataset_description,
)
from coverage_lookup import (
    extract_coverage,
    get_coverage_target,
    build_api_coverage,
    is_per_dataset_coverage,
    build_per_dataset_coverage,
)
logger = logging.getLogger(__name__)

# folder of this script - templates/, metadata/ and logs/ are located
# relative to it, so the script works from any working directory
SCRIPT_DIR = Path(__file__).resolve().parent

# load author database
def load_authors(templates_dir: str) -> dict:
    authors_file = Path(templates_dir) / "authors.json"

    if not authors_file.exists():
        logger.warning(f"Authors file does not exist: {authors_file}")
        return {}

    with open(authors_file, "r", encoding="utf-8") as f:
        return json.load(f)

# normalize the README's "author" value to a list of unique ID strings
# (yaml reads unquoted IDs like 36 as numbers, but authors.json keys are text)
def normalize_author_ids(author_ids) -> list:
    if not isinstance(author_ids, list):
        author_ids = [author_ids]

    normalized = []
    for author_id in author_ids:
        # bool is a subclass of int in Python, so it is excluded explicitly
        if isinstance(author_id, int) and not isinstance(author_id, bool):
            author_id = str(author_id)
        if not isinstance(author_id, str):
            raise ValueError(
                f"Author ID {author_id!r} in the README is not valid - "
                f'write IDs as text, e.g. author: ["36", "82"]'
            )
        if author_id in normalized:
            logger.warning(f"Author ID {author_id} is listed more than once - using it only once")
            continue
        normalized.append(author_id)

    return normalized


# resolve author IDs to full author info; an unknown ID stops the run
def resolve_authors(author_ids: list, authors_db: dict) -> list:
    unknown = [author_id for author_id in author_ids if author_id not in authors_db]
    if unknown:
        raise ValueError(
            f"Author ID(s) not found in authors.json: {', '.join(unknown)} - "
            f"check the README or add the author(s) to authors.json"
        )
    return [authors_db[author_id] for author_id in author_ids]


# normalize the README's "version" value to text
# (yaml reads an unquoted 1.10 as the number 1.1 - that cannot be undone,
# so decimal numbers are rejected instead of being converted)
def normalize_version(version) -> str:
    if isinstance(version, int) and not isinstance(version, bool):
        return str(version)
    if isinstance(version, str):
        return version
    raise ValueError(
        f"version {version!r} in the README is not valid - write it as text in quotes, "
        f'e.g. version: "1.10" (without quotes, yaml reads 1.10 as the number 1.1)'
    )


# build one author entry; only the fields SDL expects are taken from authors.json
def build_author(author: dict) -> dict:
    return {
        "givenName": author["givenName"],
        "familyName": author["familyName"],
        "identifiers": [
            {"scheme": identifier["scheme"], "value": identifier["value"]}
            for identifier in author.get("identifiers", [])
        ],
    }

# build one simulation entry (a top-level folder) as a plain dict
def build_simulation(name: str, path: str, dataset_paths: list, description) -> dict:
    return {
        "datasetPaths": dataset_paths,
        # str() keeps the output of the old Jinja templates for non-text README values
        "description": str(description),
        "name": name,
        "path": f"{path}/",
    }


# build one dataset entry (a file) as a plain dict; coverage keys are merged in if given
def build_dataset(name: str, path: str, file_format: str, file_type: str, description, coverage: dict | None = None) -> dict:
    dataset = {
        "description": str(description),
        "fileFormat": file_format,
        "name": name,
        "path": path,
        "type": file_type,
    }
    if coverage:
        dataset.update(coverage)
    return dataset

# README keys with dedicated handling (author -> "authors", version -> inside
# "versions"); every OTHER key of the yaml block is passed through as an
# additional top-level field (e.g. "keywords")
RESERVED_META_KEYS = {"name", "description", "author", "version"}
# top-level fields the generator builds itself - a README key with one of
# these names would clash with them
GENERATED_KEYS = {"authors", "versions"}


# build the complete experiment metadata as one plain dict
def build_experiment(meta: dict, authors: list, simulations: list, datasets: list) -> dict:
    extra_fields = {key: value for key, value in meta.items() if key not in RESERVED_META_KEYS}

    clashes = GENERATED_KEYS & extra_fields.keys()
    if clashes:
        raise ValueError(
            f"README yaml block must not contain the key(s) {', '.join(sorted(clashes))} - "
            f"these fields are generated"
        )

    return {
        "name": meta["name"],
        "description": meta["description"],
        **extra_fields,
        "authors": [build_author(author) for author in authors],
        "versions": [
            {
                "version": meta["version"],
                "simulations": simulations,
                "datasets": datasets,
            }
        ],
    }


# write the metadata as JSON - first to a temporary file, so that an error
# never leaves an empty or half-written output file behind
def write_output(experiment: dict, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = output_file.with_name(output_file.name + ".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(experiment, f, indent=4, ensure_ascii=False)
            f.write("\n")
    except Exception:
        tmp_file.unlink(missing_ok=True)
        raise
    tmp_file.replace(output_file)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate metadata.json for experiments"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to the experiment's data directory, e.g. ../sdl_data/sdl_exp_309. "
             "The last path segment is used as the experiment name."
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Name of the output file (default: <exp_id>_metadata.json)"
    )
    parser.add_argument(
        "--output_dir",
        default=str(SCRIPT_DIR / "metadata"),
        help="Directory for the output file (default: metadata/ next to this script)"
    )
    parser.add_argument(
        "--templates_dir",
        default=str(SCRIPT_DIR / "templates"),
        help="Path to the templates directory (default: templates/ next to this script)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # absolute and normalized, so that "./", "../x" or a trailing slash still
    # give the real folder name (symlinks are kept as given, not resolved)
    input_path = Path(os.path.abspath(args.path))  # e.g. /home/user/sdl_data/sdl_exp_309
    exp_id = input_path.name                                                # e.g. "sdl_exp_309"

    handlers = [logging.StreamHandler()]
    if args.debug:
        log_file = SCRIPT_DIR / "logs" / f"{exp_id}_run.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s: %(message)s", handlers=handlers)

    output_filename = args.output_file or f"{exp_id}_metadata.json"         # e.g. "sdl_exp_309_metadata.json"
    output_file = Path(args.output_dir) / output_filename                   # e.g. <script folder>/metadata/sdl_exp_309_metadata.json


    logger.info(f'Experiment : {exp_id}')
    logger.info(f'Input Path : {input_path}')
    logger.info(f'Output File : {output_file}')

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path is not an existing directory: {input_path}")

    if output_file.exists():
        answer = input(f"\nOutput file already exists: {output_file}\nOverwrite? [y/n]: ").strip().lower()
        if answer not in ["y", "yes", "j", "ja"]:
            logger.warning("Aborted - output file already exists and overwrite was declined")
            return

    # The README.md (in the raw experiment data directory, i.e. input_path)
    # is now the single source for both the experiment's metadata (name,
    # description, author, version, ...) and its description assignments -
    # both are read from the same embedded yaml block.
    readme_path = input_path / "README.md"
    if not readme_path.exists():
        raise FileNotFoundError(f"No README.md found in {input_path} - a README with a yaml " f"block (name, description, author, version, ...) is required")

    logger.info(f"Reading experiment metadata and descriptions from: {readme_path}")
    readme_data = load_readme_yaml(str(readme_path))
    meta = extract_meta(readme_data)
    readme_descriptions = extract_descriptions(readme_data)

    required_fields = {"name", "description", "author", "version"}
    # None, "" and [] count as missing - but not 0 (e.g. version: 0)
    missing_fields = {f for f in required_fields if meta.get(f) in (None, "", [])}
    if missing_fields:
        raise ValueError(
            f"README yaml block in {readme_path} is missing required field(s): "
            f"{', '.join(sorted(missing_fields))}"
        )
    meta["version"] = normalize_version(meta["version"])
    logger.debug(f'metadata : {meta}')

    # Optional spatialCoverage/temporalCoverage, attached further down once
    # each dataset is actually rendered. Entirely optional - everything
    # below stays None if the README has no "coverage" section at all.
    # Two forms: a single shared block (coverage_target/api_coverage) or
    # one independent coverage entry per dataset path
    # (per_dataset_coverage) - see coverage_lookup.py for both formats.

    coverage = extract_coverage(readme_data)
    per_dataset_coverage = None
    coverage_target = None
    api_coverage = None
    if coverage is not None:
        if is_per_dataset_coverage(coverage):
            per_dataset_coverage = build_per_dataset_coverage(coverage)
        else:
            coverage_target = get_coverage_target(coverage)
            api_coverage = build_api_coverage(coverage)
    coverage_applied = False
    applied_dataset_paths = set()

    # load author database
    authors_db = load_authors(args.templates_dir)

    # resolve author IDs to full author info
    authors = resolve_authors(normalize_author_ids(meta['author']), authors_db)
    logger.debug(f'authors : {authors}')


    # The README is always included as a dataset entry - every experiment
    # is expected to have one, and it's part of the data as far as SDL is
    # concerned.
    include_readme_as_dataset = True

    # Load the file_format dictionary once (stored centrally in templates_dir,
    # shared across all experiments, similar to authors.json). It is passed
    # around as a live dict reference so that newly added entries take effect
    # immediately for subsequent files in this run, without needing to reload
    # the file from disk in between.
    format_map_file = str(Path(args.templates_dir) / DEFAULT_FORMAT_MAP_FILE)
    format_map = load_format_map(format_map_file)

    # Same idea for the file_type dictionary (input/output/data_product/...
    # based on file extension), loaded once and shared across the whole run.
    type_map_file = str(Path(args.templates_dir) / DEFAULT_TYPE_MAP_FILE)
    type_map = load_type_map(type_map_file)

    # Path-keyword dictionary for file_type (e.g. "output" anywhere in the
    # path -> "output"), checked before falling back to the extension
    # dictionary above.
    type_path_map_file = str(Path(args.templates_dir) / DEFAULT_TYPE_PATH_MAP_FILE)
    type_path_map = load_path_type_map(type_path_map_file)

    # collect simulation and dataset entries as plain dicts
    simulations = []
    datasets = []

    all_items = sorted(input_path.rglob('*'))

    # Phase 1: collect all dataset paths up front and group them by their
    # top-level folder, so we can fill in "datasetPaths" for each simulation
    # entry in phase 2 (SDL appears to create implicit duplicate objects per
    # simulation if datasetPaths is left empty).
    dataset_paths_by_top_level = {}
    for item in all_items:
        if item.name == output_filename:
            continue
        if readme_path is not None and item == readme_path and not include_readme_as_dataset:
            continue
        if item.is_file():
            rel_item_parts = item.relative_to(input_path).parts
            top_level_name = rel_item_parts[0] if len(rel_item_parts) > 1 else None
            if top_level_name:
                dataset_path = item.relative_to(input_path).as_posix()
                dataset_paths_by_top_level.setdefault(top_level_name, []).append(dataset_path)

    # Phase 2: generate simulations and datasets as before, now with the
    # datasetPaths list filled in for each simulation entry.
    for item in all_items:
        # skip the output file
        if item.name == output_filename:
            continue

        # skip the README file itself if the user chose not to include it
        # as a dataset entry (it was only used to supply metadata/descriptions)
        if readme_path is not None and item == readme_path and not include_readme_as_dataset:
            continue

        if item.is_dir():
            # Only the TOP-LEVEL folders (direct children of input_path, e.g.
            # J1-J5, Mesh) are created as standalone "simulation" objects.
            # Deeper nested folders (seissol_param, mesh0, surface_cell, ...)
            # are purely structural grouping folders for files and are NOT
            # turned into their own simulation objects - otherwise every
            # nesting level would produce an additional SDL object, which
            # looks like duplicates.
            rel_dir_parts = item.relative_to(input_path).parts
            if len(rel_dir_parts) > 1:
                continue

            logger.debug(f"Generate simulation for: {item.name}")


            # Description sourced from the README's embedded yaml block
            # (see readme_description_lookup.py).
            description = get_simulation_description(readme_descriptions, item.name)

            simulation_path = item.relative_to(input_path).as_posix()
            dataset_paths = dataset_paths_by_top_level.get(item.name, [])
            simulations.append(build_simulation(item.name, simulation_path, dataset_paths, description))


        # for all files add a dataset
        elif item.is_file():
            logger.debug(f"Generate dataset for: {item.name}")
            prefix = item.parent.name
            file_name = item.name

            # Full relative path INCLUDING the file name (e.g.
            # "J1/seissol_param/job.sh", or simply "README" for files
            # directly at the root) - analogous to simulation_path for
            # folders. Prevents colliding paths for identically named files
            # in different subfolders (e.g. "mesh0/connect.bin" under every
            # Jx) and avoids the "./README" edge case for root-level files.
            rel_item_parts = item.relative_to(input_path).parts
            dataset_path = item.relative_to(input_path).as_posix()
            # Top-level folder this file lives under (e.g. "J1"), used to
            # resolve the "{folder}" placeholder in README-sourced
            # descriptions. None for files directly at the root (e.g. README
            # itself, or Mesh files if Mesh has no further nesting).
            top_level_name = rel_item_parts[0] if len(rel_item_parts) > 1 else None

            file_format = get_file_format(file_name, map_file=format_map_file, format_map=format_map)
            file_type = get_file_type(
                file_name,
                # folder path inside the experiment only, e.g. "J1/output"
                item_path=item.parent.relative_to(input_path).as_posix(),
                map_file=type_map_file,
                type_map=type_map,
                path_map_file=type_path_map_file,
                path_type_map=type_path_map,
            )

            # Description sourced from the README's embedded yaml block
            # (see readme_description_lookup.py).
            description = get_dataset_description(readme_descriptions, file_name, prefix, top_level_name)

            #  TODO: More elaborate descriptions and input|output|data product|etc

            dataset_coverage = None
            if per_dataset_coverage is not None:
                entry_coverage = per_dataset_coverage.get(dataset_path)
                if entry_coverage:
                    dataset_coverage = entry_coverage
                    coverage_applied = True
                    applied_dataset_paths.add(dataset_path)
                    logger.debug(f"Attaching per-dataset coverage to dataset: {dataset_path}")
            elif coverage is not None and (coverage_target == "all" or file_name == coverage_target):
                dataset_coverage = api_coverage
                coverage_applied = True
                logger.debug(f"Attaching coverage to dataset: {file_name}")

            datasets.append(
                build_dataset(file_name, dataset_path, file_format, file_type, description, dataset_coverage))

    if per_dataset_coverage is not None:
        missing = sorted(set(per_dataset_coverage) - applied_dataset_paths)
        if missing:
            preview = ", ".join(missing[:5]) + (", ..." if len(missing) > 5 else "")
            logger.warning(
                f"coverage entries for {len(missing)} dataset path(s) were not found among the "
                f"generated datasets and were not attached: {preview}"
            )
    elif coverage is not None and not coverage_applied:
        logger.warning(f"coverage.target '{coverage_target}' was not found among the generated "f"datasets - no coverage was attached to any dataset")


    # build the complete metadata and write it as JSON
    experiment = build_experiment(meta, authors, simulations, datasets)
    write_output(experiment, output_file)
    logger.info(f"finished, metadata written to: {output_file}")


if __name__ == '__main__':
    main()