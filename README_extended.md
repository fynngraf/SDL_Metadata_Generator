# SDL Metadata Generator — Usage Guide

A Python command-line tool that generates the metadata file required by
[SDL](https://sdl.hpc.cineca.it) for a given experiment. It scans an experiment's
data directory, classifies every file and folder, resolves author
information, and builds the result as one data structure that is written
as a single JSON metadata file — so you don't have to hand-write SDL
metadata for every experiment.

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
   `extensions`, `filename_keywords` and `folders_fallback` sections of
   the same YAML block; falls back to a generic description if a
   file/folder isn't covered.
6. Attaches the optional spatial/temporal `coverage` from the same YAML
   block to the datasets (see "Coverage" below).
7. Builds the complete metadata as one Python dictionary and writes it
   with `json.dump` (UTF-8) to the output file. The output is therefore
   always valid JSON, whatever characters the README contains.

## Requirements

- Python 3.10+ (the codebase uses `str | None` style type hints)
- Packages: `pyyaml`

```bash
pip install -r requirements.txt
```

## Directory layout

```
sdl_metadata_generator.py      # entry point; builds and writes the metadata
file_format_lookup.py          # file extension -> file format
file_type_lookup.py            # extension / path keyword -> file type
readme_description_lookup.py   # reads the README's yaml block, resolves descriptions
coverage_lookup.py             # validates and converts the optional coverage section
templates/
  authors.json                 # shared author database (author ID -> name/identifiers)
  file_format_map.json         # file extension -> file format
  file_type_map.json           # file extension -> file type
  file_type_path_map.json      # path keyword -> file type (checked before extension)
  example_README.md            # ready-to-copy README template for a new experiment
tests/
  check_golden.py              # compares the output against the reference outputs
  fixtures/                    # small experiment folders (empty files + real README)
  expected/                    # reference output for each fixture
metadata/                      # generated output lands here (created automatically)
logs/                          # log file lands here, only with --debug (created automatically)
```

The raw experiment data (and its `README.md`) lives separately, wherever
`--path` points to — it is **not** part of this repository.

## Setting up a new experiment

```bash
mkdir -p ../sdl_data/sdl_exp_NewExperiment
# copy/generate the experiment's raw data into that folder
vi ../sdl_data/sdl_exp_NewExperiment/README.md
```

A ready-to-copy template for the README's yaml block is provided in
`templates/example_README.md`. It shows every optional section.

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
- `authors` and `versions` must **not** be used as keys: the generator
  builds these fields itself and stops with an error if the README
  contains them.
- `folders`, `extensions`, `folders_fallback`, `filename_keywords` are all
  optional; see "Descriptions" below for how they're matched.
- `coverage` is optional; see "Coverage" below.

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
logs a warning (`Author ID <id> not found in authors.json - skipping`) — the run
continues, that author is simply missing from the output. Check the
console output (or `logs/<exp_id>_run.log` with `--debug`) after each run
to catch typos in author IDs.

## Descriptions

`folders`, `extensions`, `filename_keywords` and `folders_fallback`
control the `description` field of generated simulation/dataset entries.
Lookup order for a file:

1. `extensions[".ext"]` **if** written as `{description: ..., priority: true}`
2. `filename_keywords` — the first keyword (in the order listed) that
   occurs in the file name
3. `folders[<exact parent folder name>]`
4. `extensions[".ext"]` (non-priority form, i.e. a plain string)
5. `folders_fallback[<exact parent folder name>]`
6. generic fallback: `"Description of <file_name>"`

**`filename_keywords`** distinguish files that share an extension, e.g.
SeisSol's `…-volume_cell.h5` and `…-surface_cell.h5`. The file name
(without extension) is split into words at `_` and `-`; a keyword matches
if its own words appear there **next to each other and in the same
order** (case-insensitive). `volume_cell` therefore matches
`…-volume_cell.h5` but not `…-volume_vertex.h5`. List more specific
(multi-word) keywords before the shorter ones they overlap with — the
first match wins. An `extensions` entry with `priority: true` wins over
any keyword, so `.h5`/`.xdmf` must not be marked as priority if keywords
should apply to them.

For simulations (top-level folders), only `folders` is checked; unmatched
folders fall back to `"Description of <folder_name>"`.

The placeholder `{folder}` in any description is replaced with the
**top-level** run/model folder name the file is located under (not the
file's direct parent folder if it's nested deeper).

## Coverage

The optional `coverage` section adds `spatialCoverage` and/or
`temporalCoverage` to dataset entries. SDL accepts coverage only on
datasets, not on the experiment or the version. Two forms exist:

**Form 1 — one shared coverage**, attached to all datasets (default) or
to the datasets with one specific file name:

```yaml
coverage:
  temporal: {start: 2004-12-26, end: 2004-12-26}
  spatial:
    centroid: {lat: 3.3, lon: 95.9}
    polygon: "POLYGON((92.0 2.0, 98.0 2.0, 98.0 10.0, 92.0 10.0, 92.0 2.0))"  # optional
  target: all   # optional; or a file name, e.g. README.md
```

**Form 2 — coverage per dataset**, keyed by the exact dataset path as it
appears in the generated metadata:

```yaml
coverage:
  "run1/output/fault.xdmf":
    temporal: {start: 2004-12-26, end: 2004-12-26}
    spatial: {point: [95.9, 3.3], bbox: [92.0, 2.0, 98.0, 10.0]}
  "run2/output/fault.xdmf":
    spatial: {centroid: {lat: 3.3, lon: 95.9}}
```

- The form is detected automatically: if `coverage` has `temporal`,
  `spatial` or `target` as a direct key, it is form 1, otherwise form 2.
  A typo such as `spatail:` therefore silently switches to form 2.
- `temporal` and `spatial` are each optional. Dates are ISO dates
  (`YYYY-MM-DD`); for a full timestamp only the date part is kept.
- Coordinates: `centroid` takes `lat`/`lon`; `point` is `[lon, lat]`;
  `bbox` is `[minLon, minLat, maxLon, maxLat]`; `polygon` is a WKT
  `POLYGON((lon lat, ...))`. Note the order **lon before lat** in
  `point`, `bbox` and `polygon`.
- A `target` (form 1) or a dataset path (form 2) that matches no dataset
  only logs a warning; that coverage is then not attached anywhere.

## File format / file type lookup

`file_format` and `file_type` are not hard-coded in the script: they are
looked up per file in three shared JSON mapping tables in `templates/`
(`--templates_dir`). The "extension" is the part of the file name after
the last dot, lowercased (`u1.bin` → `bin`).

| Table                     | Maps                     | Example              |
|---------------------------|--------------------------|----------------------|
| `file_format_map.json`    | extension → file format  | `"h5": "HDF5"`       |
| `file_type_map.json`      | extension → file type    | `"bin": "output"`    |
| `file_type_path_map.json` | path keyword → file type | `"output": "output"` |

**`file_format`** comes from `file_format_map.json` only.

**`file_type`** is resolved in this order:

1. `file_type_map.json`, **if** the extension is written in the long form
   with `override_path` — it then wins over any path keyword:
   ```json
   {
       "csv": {"type": "product", "override_path": true}
   }
   ```
2. `file_type_path_map.json`: the first keyword that occurs anywhere in
   the file's **folder** path (case-insensitive substring match, file name
   itself excluded). Note that this is the full folder path including the
   `--path` prefix, so a keyword like `input` in a parent directory name
   matches every file. If several keywords match, the first one in the
   JSON wins — avoid overlapping keywords.
3. `file_type_map.json`, short form (`"par": "input"`).

### The tables learn new extensions

If an extension is missing from `file_format_map.json` or
`file_type_map.json`, the script stops and asks:

```
Add '.ext' to the file_format dictionary? [y/n]:
Which file_format should be set for '.ext'? (e.g. PAR):
```

Answering `y` saves the new entry to the JSON **immediately**, so it
applies to the rest of the run and to all future runs (and, since the
tables are shared, to every experiment). Answering anything else uses a
one-off fallback without saving: the uppercased extension for
`file_format`, `output` for `file_type`. To avoid the prompts — e.g. for
unattended or timed runs — add new extensions to the JSON files
beforehand. `file_type_path_map.json` never prompts; edit it manually.

### Seed values if a table is missing

If one of the three JSON files does not exist, it is recreated from small
seed dictionaries in the code (`DEFAULT_FORMAT_MAP`,
`DEFAULT_TYPE_MAP`, `DEFAULT_PATH_TYPE_MAP`). These seeds are only a
starting point and **differ from the current tables** (e.g. `par` → `PAR`
instead of `YAML`, `csv` → `data_product` instead of `product`), so keep
the JSON files in `templates/` rather than relying on them.

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
    `logs/<exp_id>_run.log` (UTF-8, overwritten on every run — no
    history is kept across runs).

## Command-line arguments

None of the arguments are marked `required=True` in `argparse` — the
script will technically start with just `python sdl_metadata_generator.py`.
In practice, though, `--path` always needs to be set explicitly (its
default `./` only resolves to a meaningful experiment name by accident).

| Argument           | Default                    | Required in practice? | Description                                                                 |
|---------------------|------------------------------|--------------------------|-------------------------------------------------------------------------------|
| `--path`            | `./`                         | **Yes** — always         | Path to the experiment's data directory, e.g. `../sdl_data/sdl_exp_309`. The last path segment is used as the experiment name (`exp_id`). |
| `--output_file`     | `<exp_id>_metadata.json`     | No                        | Name of the generated output file, written to `metadata/<output_file>`. |
| `--debug`           | off                           | No                        | Enables verbose (`DEBUG`-level) logging and a log file under `logs/`. |
| `--templates_dir`   | `./templates`                | No — **admin/advanced option**, not needed for normal use | Path to the templates directory (holds `authors.json` and the shared maps). Only relevant if that directory is moved or renamed; default matches this repo's layout. |

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
`--debug`) also writes `logs/sdl_exp_309_run.log`.

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
- **An error never destroys an existing output file.** The metadata is
  first written to `<output file>.tmp` and only then replaces the real
  file, so a failed run leaves the previous output untouched.
- **File classification is extension/path-based**, driven entirely by the
  shared JSON maps in `templates/`. Add new extensions/paths there rather
  than editing `sdl_metadata_generator.py`.
- **Unknown file extensions still trigger an interactive prompt**
  (`Add '.ext' to the file_format/file_type dictionary? [y/n]`), asking
  whether to permanently add the extension to the relevant map in
  `templates/`. This is independent of `--debug` and can make the script
  hang waiting for input if run unattended against data containing
  unfamiliar extensions (see "File format / file type lookup" above).
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

## Checking changes (reference outputs)

`tests/check_golden.py` guards against unintended changes to the output.
It runs the generator on every folder in `tests/fixtures/` and compares
the result with `tests/expected/<folder name>.json`:

```bash
python tests/check_golden.py
```

- `[OK]` = same content as the reference. Whitespace, key order and line
  endings are ignored, list order is not.
- `[FAIL]` lists the first differences by JSON path, e.g.
  `$.versions[0].version: '1.0.1' -> '1.0.0'` (reference -> new), and
  keeps the new output as `metadata/_check_<name>.json` for inspection.
- Exit code 0 = all fixtures identical, 1 = at least one difference.

The fixtures contain the real folder structure of an experiment with
**empty** files plus its real `README.md` — the generator reads only file
names, not their content. The references were generated with commit
`5245240` and intentionally keep its known quirks (e.g. `par` -> `YAML`).
When a change is **meant** to alter the output, regenerate the affected
reference and say why in the commit message.

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
