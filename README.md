# SDL Metadata Generator — Quickstart

Generates a metadata file for SDL from an experiment's data folder + its `README.md`.

## Install

```bash
pip install -r requirements.txt
```

## Experiment README.md

Place a `README.md` inside the experiment's data folder (`--path`),
containing this yaml block:

```yaml
name: "MyExperiment"
description: "Short description."
author: ["36", "82"]        # IDs from templates/authors.json
version: "1.0.0"

folders:
  run1: "Description of run1"

extensions:
  .par:
    description: "{folder}: SeisSol parameter file"
    priority: true
```

- `name`, `description`, `author`, `version` are required.
- `folders`/`extensions`/`folders_fallback` are optional; `{folder}` = top-level run folder name.
- Only a file named exactly `README.md` is read (no `README` / `README.txt`).

## Run

Must currently be started from inside the `SDL_Metadata_Generator`
directory itself:

```bash
user@system:~/SDL_Metadata_Generator$ python sdl_metadata_generator.py --path=../sdl_data/sdl_exp_309
```

- `--path` (required): path to the experiment's data folder. Last segment = experiment name.
- `--output_file` (optional, default `<exp_id>_metadata.json`): output filename.
- `--debug` (optional flag): verbose logging + debug artifacts in `logs/` — see `README_extended.md`.

Output is written to `metadata/<output filename>`. If it already exists,
you'll be asked whether to overwrite it — answering no aborts the run.

## Use the result in SDL

- **New experiment:** SDL → Create → Experiment Bulk → select the generated metadata file → then upload data via Upload.
- **Update existing:** re-run the generator → re-import via Edit Bulk.

## Planned

Eventually runnable as a standalone command from anywhere:

```bash
sdl_metadata_generator --path=<path to experiment directory>
```

made available via `export PYTHONPATH=$PYTHONPATH:/<path to SDL_Metadata_Generator>`.
Not implemented yet.

Full details (README format, authors, descriptions, `--debug`, admin options): see `README_extended.md`.
