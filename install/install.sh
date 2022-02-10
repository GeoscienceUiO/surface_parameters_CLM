#! /usr/bin/bash
set -e

# Get CTSM folder from settings file (shell argument)
PATH_OPT=$1
DIR_CTSM=$(grep -oP 'dir_ctsm\s*[=:]\s*\K(.+)' $PATH_OPT)

# Other folders/paths
DIR_CODE=$PWD/$(dirname "${BASH_SOURCE[0]}")/..
DIR_INST=$DIR_CODE/install
DIR_ENV=$DIR_CODE/env
DIR_CONF=$DIR_CODE/config

# Get CTSM (if needed)
if ! [ -d $DIR_CTSM ]; then
    module load git/2.23.0-GCCcore-8.3.0
    git clone --origin escomp https://github.com/ESCOMP/CTSM.git $DIR_CTSM
    cd $DIR_CTSM
    git checkout tags/ctsm5.1.dev043
    ./manage_externals/checkout_externals
    module purge
fi;

# CIME porting (if needed)
if ! [ -d $HOME/.cime ]; then
    module load git/2.23.0-GCCcore-8.3.0
    git clone git@github.com:MetOs-UiO/dotcime.git $HOME/.cime
    module purge
fi;

# Compile gen_domain (if needed)
cd $DIR_CTSM/cime/tools/mapping/gen_domain_files
if ! [ -f gen_domain ]; then
    cd src
    ../../../configure --macros-format Makefile --mpilib mpi-serial --machine saga
    . ./.env_mach_specific.sh ; gmake
fi;
cd $DIR_CODE

# Compile mksurfdat (if needed)
cd $DIR_CTSM/tools/mksurfdata_map
if ! [ -f mksurfdata_map ]; then
    cd src
    cp $DIR_CONF/Makefile.common ./Makefile.common
    module load netCDF-Fortran/4.5.2-iimpi-2019b
    gmake clean
    gmake -j 8
    module purge
fi;
cd $DIR_CODE

# Create virtual environment
module load Anaconda3/2020.11
if [ -d $DIR_ENV ]; then
    rm -rf $DIR_ENV
fi
python3 -m venv $DIR_ENV
source $DIR_ENV/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r $DIR_INST/requirements_3.7.txt
deactivate
module purge
