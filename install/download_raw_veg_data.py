import os, requests
from urllib3.exceptions import InsecureRequestWarning
from pathlib import Path
from sys import argv
from tqdm import tqdm

URL_SRC = 'https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/lnd/clm2/rawdata/pftcftdynharv.0.25x0.25.LUH2.histsimyr1850-2015.c170629/'
FILE = "mksrf_landuse_histclm50_LUH2_{}.c170629.nc"
DIR_DST = Path('/cluster/shared/noresm/inputdata/lnd/clm2/rawdata/pftcftdynharv.0.25x0.25.LUH2.histsimyr1850-2015.c170629/add')


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    years = range(int(argv[1]), int(argv[2]) + 1)
    failed = []
    for y in tqdm(years):
        name = FILE.format(y)
        url = os.path.join(URL_SRC, name)
        path_out = DIR_DST / name
        raw = requests.get(url, verify=False)
        if raw.status_code == requests.codes.ok:
            open(path_out, 'wb').write(raw.content)
        else:
            print(f'{y} fails')
            failed.append(f'{url}: bad requests status code (CHECK)')
            continue
    # Log failed downloads/slicings
    if len(failed):
        path_failed = DIR_DST / 'failed_downloads.log'
        with open(path_failed, 'w') as f:
            f.writelines(failed)
        print(f'{len(failed)} failed downloads/slicings listed in {path_failed}')
