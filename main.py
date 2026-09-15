import argparse
import json
#import numpy as np
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
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


# load author database
def load_authors(templates_dir: str) -> dict:
    authors_file = Path(templates_dir) / "authors.json"

    if not authors_file.exists():
        print(f"Authors file does not exist: {authors_file}")
        return {}

    with open(authors_file, 'r') as _:   # encoding='utf-8'
        return json.load(_)


# resolve author IDs to full author info
def resolve_authors(author_ids, authors_db: dict) -> list:
    # single ID as string -> convert to list
    if isinstance(author_ids, str):
        author_ids = [author_ids]

    resolved = []
    for author_id in author_ids:
        if author_id in authors_db:
            resolved.append(authors_db[author_id])
        else:
            print(f"[WARN] Author ID '{author_id}' not found in authors.json - skipping")

    return resolved


# generate authors JSON string for template
def generate_authors_str(authors: list) -> str:
    authors_list = []
    for author in authors:
        # build identifiers list
        identifiers = []
        for identifier in author.get('identifiers', []):
            identifiers.append(
                f'{{"scheme": "{identifier["scheme"]}", "value": "{identifier["value"]}"}}'
            )
        identifiers_str = ", ".join(identifiers)

        authors_list.append(
            f'{{"givenName": "{author["givenName"]}", '
            f'"familyName": "{author["familyName"]}", '
            f'"identifiers": [{identifiers_str}]}}'
        )

    return ", ".join(authors_list)


# generate experiment.json.j2 from the README's meta fields
def generate_exp_template(env: Environment, meta: dict, authors_str: str, templates_dir: str, exp_id: str):

    # Fields with dedicated handling elsewhere (author -> resolved authors_str,
    # version -> placed inside "versions[0]"). Any OTHER key present in the
    # README's yaml block is passed through automatically as an additional
    # top-level property (e.g. "keywords", "path", ...).
    reserved_keys = {"name", "description", "author", "version"}
    extra_lines = []
    for key, value in meta.items():
        if key in reserved_keys:
            continue
        # json.dumps handles quoting/escaping correctly for strings, lists,
        # numbers, dicts, etc. - safer than manual string concatenation.
        extra_lines.append(f'    {json.dumps(key)}: {json.dumps(value)},')
    extra_fields_str = ("\n".join(extra_lines) + "\n") if extra_lines else ""

    template = """\
{
    "name":        """ + json.dumps(meta['name']) + """,
    "description": """ + json.dumps(meta['description']) + """,
""" + extra_fields_str + """    "authors":     [ """ + authors_str + """ ],
    "versions":    [
        {
            "version":     """ + json.dumps(meta['version']) + """,
            "simulations": [ {{ all_simulations }} ],
            "datasets":    [ {{ all_datasets }} ]
        }
    ]
}
"""
    # save experiment.json.j2
    template_path = Path(templates_dir) / exp_id / "experiment.json.j2"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(template)

    templ = env.from_string(template)
    return templ


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate metadata.json for experiments"
    )
    parser.add_argument(
        "--path",
        default="./",
        help="Path to the base directory of experiments"
    )
    parser.add_argument(
        "--name_dir",
        default="",
        help="Name of the experiment"
    )
    parser.add_argument(
        "--output_file",
        default="metadata.json",
        help="Name of the output file"
    )
    parser.add_argument(
        "--templates_dir",
        default="./templates",
        help="Path to the templates directory"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    exp_id = args.name_dir                                                   # e.g. "sdl_exp_309"
    input_path = Path(args.path) / exp_id                                    # e.g. ./sdl_exp_309
    output_file = Path(args.templates_dir) / exp_id / args.output_file      # e.g. ./templates/sdl_exp_309/metadata.json

    print(f'Experiment : {exp_id}')
    print(f'Input Path : {input_path}')
    print(f'Output File : {output_file}')

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    # The README (in the raw experiment data directory, i.e. input_path) is
    # now the single source for both the experiment's metadata (name,
    # description, author, version, ...) and its description assignments -
    # both are read from the same embedded yaml block. Both "README" and
    # "README.txt"/"README.md" are accepted.
    readme_candidates = [input_path / "README", input_path / "README.txt", input_path / "README.md"]
    readme_path = next((p for p in readme_candidates if p.exists()), None)
    if readme_path is None:
        raise FileNotFoundError(
            f"No README/README.txt/README.md found in {input_path} - a README "
            f"with a yaml block (name, description, author, version, ...) is required"
        )

    print(f"Reading experiment metadata and descriptions from: {readme_path}")
    readme_data = load_readme_yaml(str(readme_path))
    meta = extract_meta(readme_data)
    readme_descriptions = extract_descriptions(readme_data)

    required_fields = {"name", "description", "author", "version"}
    missing_fields = {f for f in required_fields if not meta.get(f)}
    if missing_fields:
        raise ValueError(
            f"README yaml block in {readme_path} is missing required field(s): "
            f"{', '.join(sorted(missing_fields))}"
        )
    print(f'metadata : {meta}')

    # load author database
    authors_db = load_authors(args.templates_dir)

    # resolve author IDs to full author info
    authors = resolve_authors(meta['author'], authors_db)
    print(f'authors : {authors}')

    # generate authors string for template
    authors_str = generate_authors_str(authors)

    # Ask whether the README file itself should also become a dataset entry
    # in metadata.json, or whether it was only placed in the experiment
    # folder to supply metadata/description assignments and should
    # therefore be excluded from the generated output.
    answer = input(
        f"\nShould metadata also be generated for the README file itself "
        f"({readme_path.name})? [y/n]: "
    ).strip().lower()
    include_readme_as_dataset = answer in ("y", "yes", "j", "ja")
    if include_readme_as_dataset:
        print(f"-> {readme_path.name} will be included as a dataset entry.\n")
    else:
        print(f"-> {readme_path.name} will be excluded from the generated metadata.json.\n")

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

    # set Jinja2 Environment
    env = Environment(loader=FileSystemLoader(args.templates_dir))

    # load templates
    templ_s_r = env.get_template('simulation.json.j2')
    templ_d_s = env.get_template('dataset.json.j2')

    # generate experiment.json.j2 from the README's meta fields
    templ_exp = generate_exp_template(env, meta, authors_str, args.templates_dir, exp_id)

    # write general information to metadata.json
    all_s_r = ""
    all_d_s = ""

    all_items = sorted(input_path.rglob('*'))

    # Phase 1: collect all dataset paths up front and group them by their
    # top-level folder, so we can fill in "datasetPaths" for each simulation
    # entry in phase 2 (SDL appears to create implicit duplicate objects per
    # simulation if datasetPaths is left empty).
    dataset_paths_by_top_level = {}
    for item in all_items:
        if item.name == args.output_file:
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
        if item.name == args.output_file:
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

            print(f"Generate simulation for: {item.name}")
            if all_s_r:
                all_s_r += ","

            # Description sourced from the README's embedded yaml block
            # (see readme_description_lookup.py).
            description = get_simulation_description(readme_descriptions, item.name)

            simulation_path = item.relative_to(input_path).as_posix()
            dataset_paths = dataset_paths_by_top_level.get(item.name, [])
            dataset_paths_json = json.dumps(dataset_paths)
            all_s_r += templ_s_r.render(
                simulation_name=item.name,
                simulation_path=simulation_path,
                dataset_paths_json=dataset_paths_json,
                description=description
            )

        # for all files add a dataset
        elif item.is_file():
            print(f"Generate dataset for: {item.name}")
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
                item_path=str(item.parent),
                map_file=type_map_file,
                type_map=type_map,
                path_map_file=type_path_map_file,
                path_type_map=type_path_map,
            )

            # Description sourced from the README's embedded yaml block
            # (see readme_description_lookup.py).
            description = get_dataset_description(readme_descriptions, file_name, prefix, top_level_name)

            #  TODO: More elaborate descriptions and input|output|data product|etc

            if all_d_s != "": all_d_s += ","
            all_d_s += templ_d_s.render(
                prefix=prefix,
                dataset_path=dataset_path,
                file_name=file_name,
                file_format=file_format,
                description=description,
                file_type=file_type
            )

    # write metadata.json
    with open(output_file, "w") as f:
        f.write(templ_exp.render(
            **meta,
            all_simulations=all_s_r,
            all_datasets=all_d_s)
        )
    print(f"\nfinished, metadata written to: {output_file}")


if __name__ == '__main__':
    main()