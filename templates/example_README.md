# exp.NewExperiment: Short Title

Free-text description of the experiment for human readers. This part is
NOT parsed by the generator - write whatever is useful for someone
browsing the raw data (background, related publication, contact person,
...).

---

The block below is machine-readable and is used by the SDL Metadata
Generator to build the experiment's metadata.json. Keep the reserved keys
(`name`, `description`, `author`, `version`, `folders`, `extensions`,
`folders_fallback`) intact - only add/edit the entries themselves. `name`,
`description`, `author` and `version` are required; every other top-level
key (e.g. `keywords`, `path`) is optional and passed through into
metadata.json as-is. `folders`, `extensions` and `folders_fallback` are
all optional - remove any section you don't need. Use `{folder}` as a
placeholder for the name of the top-level run/model folder the file
happens to be located under.

```yaml
name: "NewExperiment"
description: "One or two sentences describing what this experiment is about."
author: ["36", "82"]
version: "1.0.0"
keywords: ["seissol", "example"]

folders:
  # Description for a top-level run/model folder (used as that folder's
  # own description), or for a structural folder that repeats identically
  # under every top-level folder.
  run1: "Rupture model run1"
  run2: "Rupture model run2"
  seissol_param: "{folder}: Input files"

extensions:
  # Description by file extension (include the leading dot).
  .sh:
    description: "{folder}: Slurm batch scheduling script"
    priority: true
  .par:
    description: "{folder}: SeisSol main parameter file"
    priority: true
  .yaml:
    description: "{folder}: Additional SeisSol parameter files"
    priority: true
  .xdmf:
    description: "{folder}: SeisSol xdmf info to use bin data from .h5 files"
    priority: true
  .h5:
    description: "{folder}: SeisSol hdf5 file"
    priority: true

folders_fallback:
  # Description for folders that are NOT top-level run folders and not
  # listed under "folders" above.
  Mesh: "Mesh-related output"
```
