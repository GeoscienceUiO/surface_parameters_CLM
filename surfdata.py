import os, re, shutil, subprocess
from sys import argv
from pathlib import Path
from configparser import ConfigParser, ExtendedInterpolation
from datetime import datetime
import xarray as xr
import cdsapi
import f90nml

def commandRun(cmd, env=None):
    print(f'\nEXECUTING\n{cmd}\n')
    proc = subprocess.run(cmd, env=env, shell=True, check=True, capture_output=True)
    print(proc.stdout)
    print('DONE!\n')
    return str(proc.stdout)


class SurfaceData:

    def __init__(self, path_settings):
        # Current folder
        self.cwd = Path.cwd()
        # Parse settings file
        self.path_settings = self.cwd / path_settings
        info = ConfigParser(interpolation=ExtendedInterpolation(),
                            inline_comment_prefixes='#')
        info.read(path_settings)
        for k in ('name', 'forcing', 'north', 'west', 'south', 'east'):
            setattr(self, k, info['space'][k])
        for k in ('dir_ctsm', 'dir_inp', 'dir_out'):
            setattr(self, k, Path(info['path'][k]))
        years = info['time']['years']
        self.compute_weights = eval(info['switch']['compute_weights'])
        # Other folders
        self.dir_weight = self.dir_out / 'weight_maps'
        # Years for which parameters are interpolated
        if '-' in years:
            ys = [int(y) for y in re.split('[ -]+', years)]
            self.years = list(range(ys[0], ys[1] + 1))
            self.res_pft_opt = ''
        else:
            self.years = [years]
            self.res_pft_opt = '-hirespft' if years[0] == 2005 else ''
        # Output paths and date stamp
        if self.compute_weights:
            if self.dir_out.exists():
                raise Exception(f"{self.dir_out} exists already!\nChange 'dir_out' in {path_settings}")
            else:
                self.today = datetime.now().strftime('%y%m%d')
                self.dir_weight.mkdir(parents=True)
        else:
            self.today = re.search(f'(\d{{6}})', list(self.dir_out.glob('domain.lnd*nc'))[0].name).group(1)
        self.path_mask = self.dir_out / f'mask_ocean_{self.name}.nc'
        self.path_scno = self.dir_out / f'SCRIPgrid_{self.name}_nomask_c{self.today}.nc'
        self.path_scma = self.dir_out / f'SCRIPgrid_{self.name}_ocean_mask_c{self.today}.nc'
        self.path_mapp = self.dir_out / f'map_{self.name}_ocean_to_land_nomask_aave_da_c{self.today}.nc'

    def main(self):
        if self.compute_weights:
            self.oceanmask()
            self.scripgrids()
            self.mappings()
            self.domains()
            self.weights()
        for year in self.years:
            self.surfdata(year)

    def oceanmask(self):
        if self.forcing == 'ERA5-Land':
            self._era5land_mask()
        elif self.forcing == 'MET_Nordic':
            self._metnordic_mask()
        else:
            raise Exception(f'Bad forcing in {self.path_settings}')

    def scripgrids(self):
        cmd_scri = "module load NCL/6.6.2-intel-2019b; " +\
                   f"ncl 'path_in=\"{self.path_mask}\"' 'path_no=\"{self.path_scno}\"' " +\
                   f"'path_ma=\"{self.path_scma}\"' scrips_rectilinear.ncl" 
        _ = commandRun(cmd_scri)
        print(f'SCRIP grid files:\nNo mask: {self.path_scno}\nOcean mask: {self.path_scma}')

    def mappings(self):
        cmd_mapp = 'module load ESMF/8.0.0-intel-2019b; ' +\
                   f'ESMF_RegridWeightGen --ignore_unmapped -s {self.path_scma} ' +\
                   f'-d {self.path_scno} -m conserve -w {self.path_mapp} --dst_regional ' +\
                   f'--src_regional --src_type SCRIP --dst_type SCRIP'
        _ = commandRun(cmd_mapp)
        print(f'Mapping file: {self.path_mapp}')

    def domains(self):
        cmd_gdom = "module load imkl/2019.5.281-iimpi-2019b; " +\
                   "module load netCDF/4.7.1-iimpi-2019b; " +\
                   "module load netCDF-Fortran/4.5.2-iimpi-2019b; " +\
                   f"{self.dir_ctsm / 'cime/tools/mapping/gen_domain_files/gen_domain'} " +\
                   f"-m {self.path_mapp} -o {self.name} -l {self.name}"
        _ = commandRun(cmd_gdom)
        pattern_fdom = f'domain.*.{self.name}*.nc'
        for _path_dom in self.cwd.glob(pattern_fdom):
            shutil.move(_path_dom, self.dir_out / _path_dom.name)
        print(f'Domain files: {self.dir_out / pattern_fdom}')

    def weights(self):
        env = os.environ.copy()
        env.update({"ESMF_NETCDF_LIBS": "'-lnetcdff -lnetcdf -lnetcdf_c++'",
                    "ESMF_COMPILER": "intel",
                    "ESMF_COMM": "openmpi",
                    "ESMF_NETCDF_LIBPATH": "/cluster/software/ESMF/8.0.0-intel-2019b/lib",
                    "ESMF_NETCDF_INCLUDE": "/cluster/software/ESMF/8.0.0-intel-2019b/include",
                    "ESMFBIN_PATH": "/cluster/software/ESMF/8.0.0-intel-2019b/bin",
                    "CSMDATA": str(self.dir_inp),
                    "MPIEXEC": "mpirun",
                    "REGRID_PROC": "1"})
        cmd_weigh = "module load ESMF/8.0.0-intel-2019b; " +\
                    "module load NCO/4.9.1-intel-2019b; " +\
                    "module load NCL/6.6.2-intel-2019b; " +\
                    f"{self.dir_ctsm / 'tools/mkmapdata/mkmapdata.sh'} " +\
                    f"-f {self.path_scno} -r {self.name} -t regional"
        _ = commandRun(cmd_weigh, env)
        for _path_map in self.cwd.glob(f"map*{self.name}*.nc"):
            shutil.move(_path_map, self.dir_weight / _path_map.name)

    def surfdata(self, year):
        print(f'\nINTERPOLATE SURFACE PARAMETERS FOR {year}:')
        # Dry-run Perl wrapper to get the namelist
        cmd_nlist = "module load netCDF-Fortran/4.5.2-iimpi-2019b; " +\
                    f"{self.dir_ctsm / 'tools/mksurfdata_map/mksurfdata.pl'} " +\
                    f"-debug -no-crop -res usrspec -usr_gname {self.name} " +\
                    f"-usr_gdate {self.today} -usr_mapdir {self.dir_weight} " +\
                    f"-dinlc {self.dir_inp} {self.res_pft_opt} -years '{year}'"
        stdout = commandRun(cmd_nlist)
        path_nlist = self.cwd / re.search(f"mksurfdata_map < (surfdata_{self.name}_.+_simyr{year}_c\d{{6}}\.namelist)", stdout).groups(0)[0]
        # Edit the namelist: regional instead of global grid
        nml = f90nml.read(path_nlist)
        nml['clmexp']['mksrf_gridtype'] = 'regional'
        nml.write(path_nlist, force=True)
        # Run executable directly with edited namelist
        cmd_surf = "module load netCDF-Fortran/4.5.2-iimpi-2019b; " +\
                   f"{self.dir_ctsm / 'tools/mksurfdata_map/mksurfdata_map'} " +\
                   f"< {path_nlist}"
        _ = commandRun(cmd_surf)
        # Move all surfdata-related files to output folder
        pattern_surf = f'surfdata_{self.name}_*'
        paths_surfall = self.cwd.glob(f'surfdata_{self.name}_*')
        for f in paths_surfall:
            shutil.move(f, self.dir_out / f.name)
            if f.name.endswith('.nc'):
                print(f'Surface parameters: {self.dir_out / f.name}')

    def _era5land_mask(self):                
        # Download sample forcing file with mask info if needed
        path_tmp = self.dir_out / 'tmp_era5land.nc'
        if not path_tmp.exists():
            area = [getattr(self, k) for k in ('north', 'west', 'south', 'east')]
            server = cdsapi.Client()
            server.retrieve('reanalysis-era5-land',
                            {'format': 'netcdf', 'area': area, 'time': '06:00',
                             'day': '01', 'month': '01', 'year': '1981',
                             'variable': 'total_precipitation'}, path_tmp)
        # Format mask files
        with xr.open_dataset(path_tmp) as nc:
            mask = nc['tp'].isnull().squeeze().drop('time') # True = ocean
        coords = {k: mask[k].values.astype(float).round(1) for k in ['latitude', 'longitude']}
        mask = mask.assign_coords(coords)
        mask.name = 'ocean_mask'
        mask.to_netcdf(self.path_mask)
        print(f'Ocean mask saved to {self.path_mask}')

if __name__ == '__main__':
    obj = SurfaceData(Path(argv[1]))
    obj.main()
