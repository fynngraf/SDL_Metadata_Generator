# This is a sample Python script.

# Press Umschalt+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# import argparse
# import numpy as np
from pathlib import Path
from sys import prefix

from jinja2 import Environment, FileSystemLoader

# parser = argparse.ArgumentParser(description="create metadata.json file from SeisSol folder")
# parser.add_argument("--path", nargs=1, metavar=("input_path"), default=("./SeisSol_Output"), help="path to SeisSol folder used as input", type=str)
# parser.add_argument("--output-file", nargs=1, metavar=("output_file"), default=("metadata.json"), help="output file", type=str)
# args = parser.parse_args()
# print(f"input_path: {input_path}")
# print(f"output_file: {output_file}")
input_path="/sdl_100runs/sdl_test/"
output_file="metadata.json"


# set Jinja2 Environment
env= Environment(loader=FileSystemLoader('.'))
templ_exp = env.get_template('templates/experiment.json.j2')
templ_s_r = env.get_template('templates/simulation.json.j2')
templ_d_s = env.get_template('templates/dataset.json.j2')

# write general information to metadata.json
# templ_exp only looks for all_simulations and all_datasets
all_s_r= ""
all_d_s= ""

# go through all directories
folder = Path(input_path)
# [x for x in p.iterdir() if x.is_dir()]
for item in folder.rglob('*'):
    # for all directories add a simulation run
    if item.is_dir():
        print(f"Generate simulation for: {item.name}")
        # templ_s_r simulation run only looks for simulation_name
        if all_s_r != "": all_s_r+=","
        all_s_r+= templ_s_r.render(simulation_name= item.name)
    if item.is_file():
        print(f"Generate file for: {item.name}")
        #  needed for temp_d_s: file_name, prefix, file_format, description
        print(f"Generate dataset for: {item}")
        prefix= item.parent.name
        file_name= item.name
        file_format= file_name.split(".")[-1]
        description= "Unknown"
        if all_d_s != "": all_d_s+=","
        all_d_s+= templ_d_s.render(prefix= prefix, file_name= file_name, file_format= file_format, description= description, file_type= "output")

with (open(output_file, "w") as f):
    f.write(templ_exp.render(all_simulations= all_s_r, all_datasets= all_d_s))




# def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    # print(f'Hi, {name}')  # Press Strg+F8 to toggle the breakpoint.



# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
