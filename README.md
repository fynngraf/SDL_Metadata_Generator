# SDL Metadata Generator — Quickstart

Generates `metadata.json` for SDL from an experiment's data folder + its README.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py --path=../sdl_data/sdl_exp_309 --output_file=metadata.json --templates_dir=./templates
```

- `--path` (required): path to the experiment's data folder. Last segment = experiment name.
- `--output_file` (optional, default `metadata.json`): output filename.
- `--templates_dir` (optional, default `./templates`): where `authors.json` and the lookup maps live.

## Experiment README

Place a `README` / `README.md` / `README.txt` inside the experiment's data
folder (`--path`), containing this yaml block:

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
- Unknown author IDs → skipped with a warning, check console output.
- No README / missing required field → script stops with an error.

## Use the result in SDL

- **New experiment:** SDL → Create → Experiment Bulk → select `metadata.json` → then upload data via Upload.
- **Update existing:** re-run the generator → re-import via Edit Bulk.

Full details: see `README_extended.md`.
