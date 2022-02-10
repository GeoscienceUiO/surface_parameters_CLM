#! /usr/bin/bash
set -e

# ./masks.sh Fennoscandia_0.1.ini

# Settings file (shell argument)
path_opt=$1

# Code folder
dir_code=$PWD/$(dirname "${BASH_SOURCE[0]}")

# Run Python program
module load Anaconda3/2020.11
source $dir_code/env/bin/activate
python3 $dir_code/surfdata.py $path_opt
deactivate
module purge
