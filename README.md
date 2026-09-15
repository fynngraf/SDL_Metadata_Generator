# SDL Metadata Generator — Usage Guide

A Python command-line tool that generates the `metadata.json` file required
by [SDL](https://sdl.hpc.cineca.it) for a given experiment. It scans an experiment's
data directory, classifies every file and folder, resolves author
information, and renders the result from Jinja2 templates into a single
metadata file — so you don't have to hand-write SDL metadata for every
experiment.

## What it does

For one experiment directory, the generator:

1. Reads the experiment's `README` (in its data directory) and parses
   the single embedded ` ```yaml ``` ` block from it. That block is the
   **only** source of both the experiment's metadata (name, description,
   authors, version, ...) and its file/folder descriptions — there is no
   separate config file per experiment.
2. Resolves the author IDs listed under `author` in that block against the
   shared `templates/authors.json` database (given/family name +
   identifiers such as ORCID) — see "Authors" below.
3. Walks the experiment directory recursively:
   - Top-level folders become **simulation** entries.
   - Every file becomes a **dataset** entry.
4. Looks up `file_format` (e.g. `YAML`, `TXT`, ...) and `file_type`
   (input / output / data product / ...) for each file via
   `templates/file_format_map.json`, `templates/file_type_map.json` and
   `templates/file_type_path_map.json`.
5. Assigns descriptions to simulations/datasets from the `folders`,
   `extensions` and `folders_fallback` sections of the same YAML block;
   falls back to a generic description if a file/folder isn't covered.
6. Renders `experiment.json.j2`, `simulation.json.j2` and `dataset.json.j2`
   and writes the combined result to `metadata.json`.

## Requirements

- Python 3.10+ (the codebase uses `str | None` style type hints)
- Packages: `jinja2`, `pyyaml`

```bash
pip install -r requirements.txt
```

## Directory layout

```
templates/
  authors.json              # shared author database (author ID -> name/identifiers)
  file_format_map.json      # file extension -> file format
  file_type_map.json        # file extension -> file type
  file_type_path_map.json   # path keyword -> file type (checked before extension)
  experiment.json.j2        # generated dynamically per run, do not hand-edit
  simulation.json.j2        # template for a simulation entry
  dataset.json.j2           # template for a dataset entry
  sdl_exp_<name>/            # generated output (experiment.json.j2, metadata.json) lands here per experiment
```

The raw experiment data (and its `README`) lives separately, wherever
`--path` points to — it is **not** part of `templates/`.

## Setting up a new experiment

```bash
mkdir -p ../sdl_data/sdl_exp_NewExperiment
# copy/generate the experiment's raw data into that folder
vi ../sdl_data/sdl_exp_NewExperiment/README
python main.py --path=../sdl_data --name_dir=sdl_exp_NewExperiment --output_file=metadata.json --templates_dir=./templates
```

A ready-to-copy template for the README's yaml block is provided
separately (`example_README.md`).

### README yaml block format

```yaml
name: "NewExperiment"
description: "One or two sentences describing what this experiment is about."
author: ["36", "82"]
version: "1.0.0"
keywords: ["seissol", "example"]

folders:
  run1: "Rupture model run1"

extensions:
  .par:
    description: "{folder}: SeisSol main parameter file"
    priority: true

folders_fallback:
  Mesh: "Mesh-related output"
```

- `name`, `description`, `author`, `version` are **required** — the
  script raises a clear error and stops if any of them is missing.
- Any other top-level key (e.g. `keywords`, `path`) is optional and is
  passed through into `metadata.json` as-is.
- `folders`, `extensions`, `folders_fallback` are all optional; see
  "Descriptions" below for how they're matched.

## Authors

Authors are **not** written out by hand in the experiment's README.
Instead, the README only lists **author IDs** (as strings) under `author`:

```yaml
author: ["36", "78", "36" ]
```

Each ID is looked up in the shared `templates/authors.json` database,
which maps an ID to the author's full information:

```json
{
  "36": {
    "givenName": "Iris",
    "familyName": "Christadler",
    "identifiers": [
      { "scheme": "orcid", "value": "0000-0002-9293-0306" }
    ]
  }
}
```

**To add a new author:** add a new entry to `templates/authors.json` with
a free-choice ID (convention so far: incrementing numeric strings), then
reference that ID from any experiment's README. The `identifiers` list is
optional but should contain an ORCID (`"scheme": "orcid"`) whenever one is
available.

An ID referenced in a README that does **not** exist in `authors.json` is
skipped with a `[WARN] Author ID '<id>' not found in authors.json` message
— the run continues, that author is simply missing from the output. Check
the console output after each run to catch typos in author IDs.

## Descriptions

`folders`, `extensions` and `folders_fallback` control the `description`
field of generated simulation/dataset entries. Lookup order for a file:

1. `extensions[".ext"]` **if** written as `{description: ..., priority: true}`
2. `folders[<exact parent folder name>]`
3. `extensions[".ext"]` (non-priority form, i.e. a plain string)
4. `folders_fallback[<exact parent folder name>]`
5. generic fallback: `"Description of <file_name>"`

For simulations (top-level folders), only `folders` is checked; unmatched
folders fall back to `"Description of <folder_name>"`.

The placeholder `{folder}` in any description is replaced with the
**top-level** run/model folder name the file is located under (not the
file's direct parent folder if it's nested deeper).

## Command-line arguments

None of the arguments are marked `required=True` in `argparse` — the
script will technically start with just `python main.py`. In practice,
though, `--name_dir` always needs to be set explicitly (its default is an
empty string, which will immediately fail); the other three have usable
defaults as long as you run the script from the repository root.

| Argument           | Default            | Required in practice? | Description                                                                 |
|---------------------|---------------------|--------------------------|-------------------------------------------------------------------------------|
| `--name_dir`        | `""`                | **Yes** — always         | Name of the experiment (matches the folder name under both `--path` and `--templates_dir`). Empty default has no valid target, so the script fails if missing. |
| `--path`            | `./`                | No, but usually set      | Base directory that contains the experiment's raw data (`<path>/<name_dir>`). Default only works if you run the script from inside that base directory itself. |
| `--templates_dir`   | `./templates`       | No                        | Path to the templates directory (holds `authors.json`, the shared maps, and every `sdl_exp_*` folder). Default matches this repo's layout — fine as-is when run from the repo root. |
| `--output_file`     | `metadata.json`     | No                        | Name of the generated output file, written to `<templates_dir>/<name_dir>/<output_file>`. Default is usually fine. |

Note: `argparse` treats `--flag=value` and `--flag value` (space instead
of `=`) as equivalent — the `=` is optional, purely a matter of style.

Example:

```bash
python main.py --path=../sdl_data --name_dir=sdl_exp_309 --output_file=metadata.json --templates_dir=./templates
```

This reads experiment data (and its README) from `../sdl_data/sdl_exp_309`,
and writes the result to `./templates/sdl_exp_309/metadata.json`.

## Things to watch out for

- **README is required.** If no `README`/`README.txt`/`README.md` is
  found in the experiment's data directory, or it has no embedded
  ` ```yaml ``` ` block, or that block is missing a required field, the
  script raises an error and stops — there is no silent fallback anymore.
- **Interactive prompt:** the script asks on stdin whether the README file
  itself should also be included as a dataset entry (`y`/`n`). Don't run
  it unattended (e.g. in CI) without piping an answer.
- **`experiment.json.j2` is regenerated on every run** from the README's
  meta fields and overwritten under
  `<templates_dir>/<name_dir>/experiment.json.j2` — do not hand-edit it,
  your changes will be lost on the next run.
- **File classification is extension/path-based**, driven entirely by the
  shared JSON maps in `templates/`. Add new extensions/paths there rather
  than editing `main.py`.
- **Nesting:** only direct top-level folders of the experiment directory
  become `simulation` entries; deeper nested folders are treated purely as
  structural grouping and do not get their own simulation object.
- The output path is derived from `--templates_dir`/`--name_dir`, **not**
  from `--path` — make sure both point at the same experiment name.

## Using the generated metadata.json in SDL

The `metadata.json` generated by this tool can be used in SDL (https://sdl.hpc.cineca.it) both
to **create a new experiment** and to **update the metadata of an
existing one**.

**Creating a new experiment:**
1. In SDL, click **Create → Experiment Bulk**.
2. Select the generated `metadata.json` file.
3. SDL creates the experiment structure together with its metadata.
4. Afterwards, upload the actual data files via **Upload**.

**Updating an existing experiment's metadata:** re-run the generator
(e.g. after editing the experiment's README) and re-import the resulting
`metadata.json` via **Edit Bulk**.
