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
  # that share the same extension but differ in a keyword in the file
  # name. SeisSol's naming: Prefix-SlurmID-outputfilename, where
  # outputfilename is {volume|surface|fault}_{cell|vertex}.h5 or
  # {volume|surface|fault}.xdmf. A keyword can be one word ("surface") or
  # several words joined with "_"/"-" ("volume_cell") - a multi-word
  # keyword only matches where its words are adjacent, in that order, so
  # "volume_cell" and "volume_vertex" below get different descriptions
  # even though both contain "volume". List more specific (multi-word)
  # keywords before the shorter ones they overlap with - list order is
  # priority order. Note: ".xdmf"/".h5" above must NOT be "priority: true",
  # otherwise these entries would never be reached.
  volume_cell: "{folder}: stress field volume output (cell-centered)"
  volume_vertex: "{folder}: stress field volume output (vertex-centered)"
  surface_cell: "{folder}: surface output (cell-centered)"
  surface_vertex: "{folder}: surface output (vertex-centered)"
  fault_cell: "{folder}: fault output (cell-centered)"
  fault_vertex: "{folder}: fault output (vertex-centered)"
  volume: "{folder}: stress field volume output"      # .xdmf variant, no cell/vertex suffix
  surface: "{folder}: surface output"                  # .xdmf variant
  fault: "{folder}: fault output"                      # .xdmf variant
  receiver: "{folder}: receiver output"
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