import argparse
import json
#import numpy as np
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


# load metadata
def load_exp_meta(exp_path: Path) -> dict:
    # complete path
    meta_file = exp_path / "exp.meta.json"

    if not meta_file.exists():
        print(f"Metadata file does not exist: {meta_file} - use default")
        return {
            "name": exp_path.name,
            "author": [],
            "version": "unknown",
            "description": ""
        }
    with open(meta_file, 'r') as _:   # encoding='utf-8'
        return json.load(_)


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
    # single ID as string → convert to list
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


# generate experiment.json.j2 from exp.meta.json
def generate_exp_template(env: Environment, meta: dict, authors_str: str, templates_dir: str, exp_id: str):

    template = """\
{
    "name":        \"""" + meta['name'] + """\",
    "version":     \"""" + meta['version'] + """\",
    "description": \"""" + meta['description'] + """\",
    "authors":     [ """ + authors_str + """ ],
    "simulations": [ {{ all_simulations }} ],
    "datasets":    [ {{ all_datasets }} ]
}
"""
    # save experiment.json.j2
    template_path = Path(templates_dir) / exp_id / "experiment.json.j2"
    with open(template_path, "w") as f:
        f.write(template)

    templ = env.from_string(template)
    return templ


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate metadata.json for experiments"
    )
    parser.add_argument(
        "--sdl_dir",
        default="./",
        help="Path to the base directory of experiments"
    )
    parser.add_argument(
        "--exp",
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

    exp_id = args.exp                            # e.g. "sdl_exp_309"
    input_path = Path(args.sdl_dir) / exp_id     # e.g. ./sdl_exp_309
    output_file = input_path / args.output_file  # e.g. ./sdl_exp_309/metadata.json

    print(f'Experiment : {exp_id}')
    print(f'Input Path : {input_path}')
    print(f'Output File : {output_file}')

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    # read exp.meta.json from templates/sdl_exp_xyz/
    meta = load_exp_meta(Path(args.templates_dir) / exp_id)
    print(f'metadata : {meta}')

    # load author database
    authors_db = load_authors(args.templates_dir)

    # resolve author IDs to full author info
    authors = resolve_authors(meta['author'], authors_db)
    print(f'authors : {authors}')

    # generate authors string for template
    authors_str = generate_authors_str(authors)

    # set Jinja2 Environment
    env = Environment(loader=FileSystemLoader(args.templates_dir))

    # load templates
    templ_s_r = env.get_template('simulation.json.j2')
    templ_d_s = env.get_template('dataset.json.j2')

    # generate experiment.json.j2 from exp.meta.json dynamically
    templ_exp = generate_exp_template(env, meta, authors_str, args.templates_dir, exp_id)

    # write general information to metadata.json
    all_s_r = ""
    all_d_s = ""

    # go through all directories
    for item in sorted(input_path.rglob('*')):
        # skip exp.meta.json and output file
        if item.name in ("exp.meta.json", args.output_file):
            continue

        if item.is_dir():
            print(f"Generate simulation for: {item.name}")
            if all_s_r:
                all_s_r += ","
            all_s_r += templ_s_r.render(simulation_name=item.name)

        # for all files add a dataset
        elif item.is_file():
            print(f"Generate dataset for: {item.name}")
            prefix = item.parent.name
            file_name = item.name
            file_format = file_name.split(".")[-1]
            description = "Unknown"

            #  TODO: More elaborate descriptions and input|output|data product|etc
            #  needed for temp_d_s: file_name, prefix, file_format, description, file_type

            # set file_type from path_info
            if "input" in str(item).lower():
                file_type = "input"
            else:
                file_type = "output"

            if all_d_s != "": all_d_s += ","
            all_d_s += templ_d_s.render(
                prefix=prefix,
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