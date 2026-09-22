# SDL Metadata Generator — Usage Guide

A Python command-line tool that generates the metadata file required by
[SDL](https://sdl.hpc.cineca.it) for a given experiment. It scans an experiment's
data directory, classifies every file and folder, resolves author
information, and renders the result from Jinja2 templates into a single
metadata file — so you don't have to hand-write SDL metadata for every
experiment.

## What it does

For one experiment directory, the generator:

1. Reads the experiment's `README.md` and parses the single embedded
   ` ```yaml ``` ` block from it. That block is the **only** source of
   both the experiment's metadata (name, description, authors, version,
   ...) and its file/folder descriptions — there is no separate config
   file per experiment.
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
   and writes the combined result to the output file.

## Requirements

- Python 3.10+ (the codebase uses `str | None` style type hints)
- Packages: `jinja2`, `pyyaml`

```bash
pip install -r requirements.txt
```

## Directory layout

```
sdl_metadata_generator.py   # entry point
file_format_lookup.py
file_type_lookup.py
readme_description_lookup.py
templates/
  authors.json              # shared author database (author ID -> name/identifiers)
  file_format_map.json      # file extension -> file format
  file_type_map.json        # file extension -> file type
  file_type_path_map.json   # path keyword -> file type (checked before extension)
  dataset.json.j2           # template for a dataset entry
  simulation.json.j2        # template for a simulation entry
metadata/                   # generated output lands here (created automatically)
logs/                       # debug artifacts land here, only with --debug (created automatically)
```

The raw experiment data (and its `README.md`) lives separately, wherever
`--path` points to — it is **not** part of this repository.

## Setting up a new experiment

```bash
mkdir -p ../sdl_data/sdl_exp_NewExperiment
# copy/generate the experiment's raw data into that folder
vi ../sdl_data/sdl_exp_NewExperiment/README.md
```

A ready-to-copy template for the README's yaml block is provided
separately (`example_README.md`).

Only a file named exactly `README.md` is read — `README` (no extension)
and `README.txt` are **not** accepted (this was different in earlier
versions of the tool).

### README.md yaml block format

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
  script raises a clear error and stops if any of them is missing or
  empty (an empty string/list counts as missing, not just an absent key).
- Any other top-level key (e.g. `keywords`, `path`) is optional and is
  passed through into the metadata file as-is.
- `folders`, `extensions`, `folders_fallback` are all optional; see
  "Descriptions" below for how they're matched.

## Authors

Authors are **not** written out by hand in the experiment's `README.md`.
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
reference that ID from any experiment's `README.md`. The `identifiers`
list is optional but should contain an ORCID (`"scheme": "orcid"`)
whenever one is available.

An ID referenced in a README that does **not** exist in `authors.json`
logs a warning (`Author ID '<id>' not found in authors.json`) — the run
continues, that author is simply missing from the output. Check the
console output (or `logs/<exp_id>_run.log` with `--debug`) after each run
to catch typos in author IDs.

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

## Running the script

The script currently must be started from **inside the
`SDL_Metadata_Generator` directory itself**:

```bash
user@system:~/SDL_Metadata_Generator$ python sdl_metadata_generator.py --path=../sdl_data/sdl_exp_309
```

This is because `--templates_dir` defaults to the relative path
`./templates`, which only resolves correctly when the current working
directory is the repository root. See "Planned" at the end of this
document for how this is intended to change.

### Output file

By default, the output filename is `<exp_id>_metadata.json`, where
`exp_id` is the last path segment of `--path` (e.g. `sdl_exp_309` →
`sdl_exp_309_metadata.json`). Override it with `--output_file`.

The file is written to `metadata/<output_filename>` (flat, directly under
the repository root, not per experiment) — the `metadata/` folder is
created automatically if it doesn't exist.

If the resulting output file already exists, the script asks:

```
Output file already exists: <path>
Overwrite? [y/n]:
```

Answering anything other than `y`/`yes`/`j`/`ja` aborts the run without
writing anything. This means the script is **not safe to run fully
unattended** (e.g. in CI) once an output file already exists, unless the
answer is piped in.

### Logging and `--debug`

The script uses Python's `logging` module instead of plain `print()`.

- **Without `--debug`**: only `INFO`-level (and above) messages are shown
  on the console — the normal status output.
- **With `--debug`**:
  - `DEBUG`-level messages are shown too (per-file/per-simulation detail,
    which rule decided a `file_type`, etc.).
  - The same log output is additionally written to
    `logs/<exp_id>_run.log` (overwritten on every run — no history is
    kept across runs).
  - The intermediate artifact `logs/<exp_id>_experiment.json.j2` is
    written (also overwritten on every run). Without `--debug`, this file
    is **not** written at all.

## Command-line arguments

None of the arguments are marked `required=True` in `argparse` — the
script will technically start with just `python sdl_metadata_generator.py`.
In practice, though, `--path` always needs to be set explicitly (its
default `./` only resolves to a meaningful experiment name by accident).

| Argument           | Default                    | Required in practice? | Description                                                                 |
|---------------------|------------------------------|--------------------------|-------------------------------------------------------------------------------|
| `--path`            | `./`                         | **Yes** — always         | Path to the experiment's data directory, e.g. `../sdl_data/sdl_exp_309`. The last path segment is used as the experiment name (`exp_id`). |
| `--output_file`     | `<exp_id>_metadata.json`     | No                        | Name of the generated output file, written to `metadata/<output_file>`. |
| `--debug`           | off                           | No                        | Enables verbose (`DEBUG`-level) logging, a log file under `logs/`, and writes the intermediate `experiment.json.j2` artifact under `logs/`. |
| `--templates_dir`   | `./templates`                | No — **admin/advanced option**, not needed for normal use | Path to the templates directory (holds `authors.json`, the shared maps, and `dataset.json.j2`/`simulation.json.j2`). Only relevant if that directory is moved or renamed; default matches this repo's layout. |

Note: `argparse` treats `--flag=value` and `--flag value` (space instead
of `=`) as equivalent — the `=` is optional, purely a matter of style.
`--debug` takes no value at all (`store_true`) — just add the flag.

Example:

```bash
python sdl_metadata_generator.py --path=../sdl_data/sdl_exp_309 --debug
```

This reads experiment data (and `README.md`) from `../sdl_data/sdl_exp_309`,
derives the experiment name `sdl_exp_309` from the last path segment,
writes the result to `metadata/sdl_exp_309_metadata.json`, and (because of
`--debug`) also writes `logs/sdl_exp_309_run.log` and
`logs/sdl_exp_309_experiment.json.j2`.

## Things to watch out for

- **README.md is required.** If no `README.md` is found in the
  experiment's data directory, or it has no embedded ` ```yaml ``` `
  block, or that block is missing a required field (or has an empty
  value for one), the script raises an error and stops — there is no
  silent fallback.
- **Only `README.md` is accepted** — `README` and `README.txt` are not
  read anymore.
- **The README is always included as a dataset entry** in the generated
  metadata file — there's no prompt or way to exclude it.
- **Overwrite prompt:** if the output file already exists, the script
  asks interactively whether to overwrite it (see "Output file" above).
- **`experiment.json.j2` is only written with `--debug`**, to `logs/`
  (see "Logging and --debug" above) — without `--debug` it is not
  generated at all.
- **File classification is extension/path-based**, driven entirely by the
  shared JSON maps in `templates/`. Add new extensions/paths there rather
  than editing `sdl_metadata_generator.py`.
- **Unknown file extensions still trigger an interactive prompt**
  (`Add '.ext' to the file_format/file_type dictionary? [y/n]`), asking
  whether to permanently add the extension to the relevant map in
  `templates/`. This is independent of `--debug` and can make the script
  hang waiting for input if run unattended against data containing
  unfamiliar extensions.
- **The recursive file scan (`--path`) does not exclude hidden folders**
  such as `.git`. Pointing `--path` at (or into) a git repository will
  walk its `.git/` contents too, likely triggering many of the "unknown
  extension" prompts above for files like `.git/hooks/*.sample`. Known
  limitation, not yet fixed — make sure `--path` points only at the
  actual experiment data.
- **Nesting:** only direct top-level folders of the experiment directory
  become `simulation` entries; deeper nested folders are treated purely as
  structural grouping and do not get their own simulation object.
- **The experiment name (`exp_id`) is derived from `--path`'s last path
  segment**, and is used both to locate the raw data (`--path` itself) and
  to build the default output filename and the `logs/` filenames. A
  trailing slash in `--path` (e.g. `../sdl_data/sdl_exp_309/`) is fine —
  it doesn't change the derived name.
- **Must be run from inside the repository** — see "Running the script"
  above.

## Using the generated metadata file in SDL

The metadata file generated by this tool can be used in [SDL](https://sdl.hpc.cineca.it) both
to **create a new experiment** and to **update the metadata of an
existing one**.

**Creating a new experiment:**
1. In SDL, click **Create → Experiment Bulk**.
2. Select the generated metadata file.
3. SDL creates the experiment structure together with its metadata.
4. Afterwards, upload the actual data files via **Upload**.

**Updating an existing experiment's metadata:** re-run the generator
(e.g. after editing the experiment's `README.md`) and re-import the
resulting metadata file via **Edit Bulk**.

## Planned

The script is intended to eventually be runnable as a standalone command
from anywhere, without needing to `cd` into this repository first:

```bash
sdl_metadata_generator --path=<path to experiment directory>
```

made available via:

```bash
export PYTHONPATH=$PYTHONPATH:/<path to SDL_Metadata_Generator>
```

Not implemented yet — for now, run `python sdl_metadata_generator.py ...`
from inside the `SDL_Metadata_Generator` directory as described in
"Running the script".
