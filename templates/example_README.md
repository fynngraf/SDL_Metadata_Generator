# exp.NewExperiment: Short Title

Free-text description of the experiment for human readers. This part is
NOT parsed by the generator - write whatever is useful for someone
browsing the raw data (background, related publication, contact person,
...).

---

The block below is machine-readable and is used by the SDL Metadata
Generator to build the experiment's metadata.json. Keep the reserved keys
(`name`, `description`, `author`, `version`, `folders`, `extensions`,
`folders_fallback`, `filename_keywords`, `coverage`) intact - only
add/edit the entries themselves. `name`, `description`, `author` and
`version` are required; every other top-level key (e.g. `keywords`,
`path`) is optional and passed through into metadata.json as-is.
`folders`, `extensions`, `folders_fallback`, `filename_keywords` and
`coverage` are all optional - remove any section you don't need. Use
`{folder}` as a placeholder for the name of the top-level run/model
folder the file happens to be located under.

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
  .h5:
    description: "{folder}: SeisSol hdf5 file"

folders_fallback:
  # Description for folders that are NOT top-level run folders and not
  # listed under "folders" above.
  Mesh: "Mesh-related output"

filename_keywords:
  # More specific than "extensions" - distinguishes SeisSol output files
  # that share the same extension but differ in a keyword placed right
  # before it (e.g. run_normal-surface_cell.h5 -> "surface", not "cell").
  # Matched as a whole token (split on "_"/"-", case-insensitive), checked
  # in this order - list more specific keywords before the generic ones
  # they can appear together with. Note: ".xdmf"/".h5" above must NOT be
  # "priority: true", otherwise these entries would never be reached.
  surface: "{folder}: surface output"
  fault: "{folder}: fault output"
  cell: "{folder}: volume (stress field) output"
  vertex: "{folder}: volume (stress field) output"
  energy: "{folder}: energy output"
  clustering: "{folder}: technical output"
  flops: "{folder}: technical output"
  threadPinning: "{folder}: technical output"
  miniSeissol: "{folder}: technical output"

coverage:
  # Optional spatial/temporal coverage. By default (no "target" given) it
  # is attached to every generated dataset entry ("all"); give an explicit
  # "target" to attach it to exactly one dataset instead. "temporal" and
  # "spatial" are each optional on their own - remove the whole "coverage"
  # section if you don't need it at all.
  temporal: {start: 2011-03-11, end: 2011-03-11}
  spatial:
    centroid: {lat: 38.3, lon: 142.4}
    polygon: "POLYGON((141.0 35.5, 145.0 35.5, 145.0 40.5, 141.0 40.5, 141.0 35.5))"  # optional
  target: all  # optional, default shown - or a specific dataset filename, e.g. README.md
```
