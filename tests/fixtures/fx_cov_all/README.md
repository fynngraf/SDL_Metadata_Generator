# Exp.266 TA_CapCosSC-HPC

Geo-INQUIRE TA Project CapCosSC-HPC (C2-TA2-531-1-2, Elizabeth Madden, San José State University). Result datasets for a suite of megathrust earthquake scenarios based on the 2004 Sumatra-Andaman earthquake. Initial conditions for these scenarios vary in the amount of pore fluid pressure and how it is distributed with depth, the relative magnitudes of the principal stresses, and initial stress heterogeneity. As a result, the modeled earthquakes vary in magnitude, average stress drop magnitude, the distribution of stress drop along the main fault, and locations of peak slip and slip rate. Generated with SeisSol on Leonardo@CINECA.

Authors:
  Elizabeth Madden
  Thomas Ulrich
  Christadler Iris
  Gabriel Alice-Agnes

Organization:
  LMU
  San José State University (add)
  
Project:
  Geo-INQUIRE (is funding)
    
Creator:
  Iris
    
Collaborators:
  Betsy (editor)
  Fynn (editor)
    
Keywords:
  seissol, geo-inquire, ta, capcossc-hpc, leonardo, numerical simulation
    
2004 Sumatra-Andaman EQ
spatial+temporal coverage might already be in the data (SDL is down)
 
spatial coverage:
  centroid: 
  
temporal coverage:
  start: 
  end: 

License:
  CC-BY-4.0


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
name: "TA_CapCosSC-HPC"
description: "Geo-INQUIRE TA Project CapCosSC-HPC (C2-TA2-531-1-2, Elizabeth Madden, San José State University). Result datasets for a suite of megathrust earthquake scenarios based on the 2004 Sumatra-Andaman earthquake. Initial conditions for these scenarios vary in the amount of pore fluid pressure and how it is distributed with depth, the relative magnitudes of the principal stresses, and initial stress heterogeneity. As a result, the modeled earthquakes vary in magnitude, average stress drop magnitude, the distribution of stress drop along the main fault, and locations of peak slip and slip rate. Generated with SeisSol on Leonardo@CINECA."
author: ["68", "81", "36", "82"]
version: "1.0.0"
keywords: ["seissol", "geo-inquire", "ta", "capcossc-hpc", "leonardo", "numerical simulation"]

folders:
  # Description for a top-level run/model folder (used as that folder's
  # own description), or for a structural folder that repeats identically
  # under every top-level folder.
  Phi03_scen4_32829263: "Simulation Results for Scenario4 with Phi03"
  Phi03_scen6_32911609: "Simulation Results for Scenario6 with Phi03"
  Phi07_Scen4_32606199: "Simulation Results for Scenario4 with Phi07"
  Phi07_Scen6_32765192: "Simulation Results for Scenario6 with Phi07"

extensions:
  # Description by file extension (include the leading dot).
  .sh:
      description:  "{folder}: Slurm batch scheduling script"
      priority: true
  .err:
    description: "{folder}: Slurm batch scheduling output (STDERR)"
    priority: true
  .out:
    description: "{folder}: Slurm batch scheduling output (STDOUT)"
    priority: true
  .par: 
    description: "{folder}: SeisSol main parameter file (draws in .yaml files)"
    priority: true
  .yaml:
    description: "{folder}: Additional SeisSol parameter files"
    priority: true
  .xdmf:
    description: "{folder}: SeisSol xdmf output to read hdf5"
    priority: true
  .h5:
    description: "{folder}: SeisSol hdf5 output"
    priority: true
  # CSV here are all output files!
  .csv:
    description: "{folder}: SeisSol output"
    priority: true

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
  temporal: {start: 2004-12-26, end: 2004-12-26}
  spatial:
    centroid: {lat: 3.3, lon: 95.9}
    polygon: "POLYGON((92.0 2.0, 98.0 2.0, 98.0 10.0, 92.0 10.0, 92.0 2.0))"
  target: all
```