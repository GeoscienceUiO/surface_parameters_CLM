load "/cluster/software/NCL/6.6.2-intel-2019b/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl"

begin
    f = addfile(path_in, "r")
    lat = f->latitude(::-1)
    lon = f->longitude(:)
    landsea = f->ocean_mask(::-1,:)
    opt = True
    opt@ForceOverwrite = True
    opt@PrintTimings = True
    rectilinear_to_SCRIP(path_no, lat, lon, opt)
    opt@GridMask = landsea
    rectilinear_to_SCRIP(path_ma, lat, lon, opt)
end
