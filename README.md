# CLM land surface parameter files

These scripts create CLM land surface parameter files for regional domains
on regular geographic grids.
They were tested on Saga using
- commit [30a2b73](https://github.com/MetOs-UiO/dotcime/commit/30a2b73996a951277c874d9f28ea82a00427ffb2)
  of [dotcime](https://github.com/MetOs-UiO/dotcime)
- and version tags/ctsm5.1.dev043 of CTSM.


## 1. Install dependencies

To install dependencies, run
bash```
./install/install.sh Fennoscandia_0.1.ini
```
where `Fennoscandia_0.1.ini` is a settings file containing the information
needed to generate land surface parameters.

Check carefully the commands in `install/install.sh` before executing it.
It is safer to execute the steps manually in a bash shell.


## 2. Generate a land surface parameter file

Run
bash```
./run_surfdata.sh Fennoscandia_0.1.ini
```
This will create a land surface parameter file for the region defined in
`Fennoscandia_0.1.ini`, i.e. a domain covering Fennoscandia (3-35E, 54-72N)
at 0.1 degree resolution using ERA5-Land land mask.
The reference year for land surface data is 2005.
Land surface parameters are interpolated from high resolution CTSM data files.
