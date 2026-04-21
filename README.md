# SDL Metadata Generator

will generate metadata for the https://sdl....

## Usage
```bash
python main.py --outfile...
```

## Installation

requirements.txt (with all python packages)

## Intended Use

```bash
cd templates
mkdir sdl_exp_NewDIR
cp sdl_exp_blueprint/exp_meta.json sdl_exp_NewDIR/exp_meta.json
vi sdl_exp_NewDIR/exp_meta.json
cp sdl_exp_blueprint/dataset.json.j2 sdl_exp_NewDIR/dataset.json.j2
vi sdl_exp_NewDIR/dataset.json.j2
cp sdl_exp_blueprint/simulation.json.j2 sdl_exp_NewDIR/simulation.json.j2
ls
cd ..
python main.py --outfile=metadata.json --exp=sdl_exp_NewDir --sdl_dir=../sdl_data/NewDir
```
