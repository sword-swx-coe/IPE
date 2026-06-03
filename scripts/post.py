import numpy as np
from netCDF4 import Dataset
from multiprocessing import Pool
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import glob
from os import path, remove
from datetime import datetime

class Grid:
  def __init__(self, path):
    # nlp, nmp, nfluxtube, nlon_geo, nlat_geo, nheights_geo
    # flux_tube_max(lp), facfac_interface, ii[1-4]_interface, dd_interface
    g = Dataset(path)

    self.nlp          = len(g.dimensions['phony_dim_0'])
    self.nfluxtube    = len(g.dimensions['phony_dim_1'])
    self.nmp          = len(g.dimensions['phony_dim_2'])
    self.nlon_geo     = len(g.dimensions['phony_dim_3'])
    self.nlat_geo     = len(g.dimensions['phony_dim_4'])
    self.nheights_geo = len(g.dimensions['phony_dim_5'])

    self.flux_tube_max = g.variables['tube_max'][:]

    self.longitude_geo = np.zeros(self.nlon_geo)
    self.latitude_geo  = np.zeros(self.nlat_geo)
    self.altitude_geo  = np.zeros(self.nheights_geo)

    for i in range(self.nlon_geo):
      self.longitude_geo[i] = i * 360. / self.nlon_geo

    for i in range(self.nlat_geo):
      self.latitude_geo[i]  = -90. + i * 180. / (self.nlat_geo-1)

    dAlt = 5.0
    self.altitude_geo[0]  = 90.
    for i in range(1, self.nheights_geo):
      if (self.altitude_geo[i-1] >= 400.0):
        dAlt = 10.0
      if (self.altitude_geo[i-1] >= 1200.0):
        dAlt = 20.0
      self.altitude_geo[i]  = self.altitude_geo[i-1] + dAlt


    self.facfac_interface = np.zeros( (3, self.nlon_geo, self.nlat_geo, self.nheights_geo) )
    self.dd_interface     = np.zeros( (3, self.nlon_geo, self.nlat_geo, self.nheights_geo) )
    self.ii1_interface    = np.zeros( (3, self.nlon_geo, self.nlat_geo, self.nheights_geo) )
    self.ii3_interface    = np.zeros( (3, self.nlon_geo, self.nlat_geo, self.nheights_geo) )
    self.ii4_interface    = np.zeros( (3, self.nlon_geo, self.nlat_geo, self.nheights_geo) )

    self.facfac_interface[0] = g.variables['fac_1'][:]
    self.facfac_interface[1] = g.variables['fac_2'][:]
    self.facfac_interface[2] = g.variables['fac_3'][:]

    self.dd_interface[0] = 1. / g.variables['dd_1'][:]
    self.dd_interface[1] = 1. / g.variables['dd_2'][:]
    self.dd_interface[2] = 1. / g.variables['dd_3'][:]
    self.dtot_inv = np.sum(self.dd_interface,axis=0)

    self.ii1_interface[0] = g.variables['ii1_1'][:]
    self.ii1_interface[1] = g.variables['ii1_2'][:]
    self.ii1_interface[2] = g.variables['ii1_3'][:]

    self.ii3_interface[0] = g.variables['ii3_1'][:]
    self.ii3_interface[1] = g.variables['ii3_2'][:]
    self.ii3_interface[2] = g.variables['ii3_3'][:]

    self.ii4_interface[0] = g.variables['ii4_1'][:]
    self.ii4_interface[1] = g.variables['ii4_2'][:]
    self.ii4_interface[2] = g.variables['ii4_3'][:]

    self.npts = np.sum(self.flux_tube_max*self.nlp)

    npts = 0
    self.ilp_map = np.zeros( (2, self.npts) )
    for lp in range(self.nlp):
      for i in range(self.flux_tube_max[lp]):
        self.ilp_map[0,npts] = i
        self.ilp_map[1,npts] = lp
        npts += 1

  def interpolate_to_geogrid(self, apex_data):
    geo_data = np.zeros( (self.nlon_geo, self.nlat_geo, self.nheights_geo) )

    factor = self.facfac_interface

    for i in range(3):
      mp  = (self.ii1_interface[i]-1).astype(np.int32) # nlon, nlat, nheights
      in2 = (self.ii3_interface[i]-1).astype(np.int32) # nlon, nlat, nheights
      in1 = (self.ii4_interface[i]-1).astype(np.int32) # nlon, nlat, nheights

      iFlux2 = self.ilp_map[0,in2].astype(np.int32)    # nlon, nlat, nheights
      lp2    = self.ilp_map[1,in2].astype(np.int32)    # nlon, nlat, nheights

      iFlux1 = self.ilp_map[0,in1].astype(np.int32)    # nlon, nlat, nheights
      lp1    = self.ilp_map[1,in1].astype(np.int32)    # nlon, nlat, nheights

      geo_data += ((apex_data[mp,lp2,iFlux2] - apex_data[mp,lp1,iFlux1])*factor[i] + apex_data[mp,lp1,iFlux1]) * self.dd_interface[i]

    return geo_data / self.dtot_inv

class Plasma:
  def __init__(self, filename, nlp, nmp, nfluxtube):
    self.ion_densities = np.zeros( (9, nmp, nlp, nfluxtube) )

    f = Dataset(filename)

    self.ion_densities[0] = f.variables['o_plus_density'][:]
    self.ion_densities[1] = f.variables['h_plus_density'][:]
    self.ion_densities[2] = f.variables['he_plus_density'][:]
    self.ion_densities[3] = f.variables['n_plus_density'][:]
    self.ion_densities[4] = f.variables['no_plus_density'][:]
    self.ion_densities[5] = f.variables['o2_plus_density'][:]
    self.ion_densities[6] = f.variables['n2_plus_density'][:]
    self.ion_densities[7] = f.variables['o_plus_2D_density'][:]
    self.ion_densities[8] = f.variables['o_plus_2P_density'][:]
    self.tec              = np.sum(self.ion_densities,axis=0)
    self.electron_temperature = f.variables['electron_temperature'][:]
    self.ion_temperature      = f.variables['ion_temperature'][:]

class Neutral:
  def __init__(self, filename, nlp, nmp, nfluxtube):
    self.velocity_apex = np.zeros( (3, nmp, nlp, nfluxtube) )
    self.velocity_geo  = np.zeros( (3, nmp, nlp, nfluxtube) )

    f = Dataset(filename)

    self.oxygen              = f.variables['o_density'][:]
    self.hydrogen            = f.variables['h_density'][:]
    self.helium              = f.variables['he_density'][:]
    self.nitrogen            = f.variables['n_density'][:]
    self.molecular_oxygen    = f.variables['o2_density'][:]
    self.molecular_nitrogen  = f.variables['n2_density'][:]
    self.neutral_temperature = f.variables['neutral_temperature'][:]
    self.velocity_apex[0]    = f.variables['neutral_apex1_velocity'][:]
    self.velocity_apex[1]    = f.variables['neutral_apex2_velocity'][:]
    self.velocity_apex[2]    = f.variables['neutral_apex3_velocity'][:]
    try:
      self.velocity_geo[0]     = f.variables['neutral_geographic_velocity1'][:]
      self.velocity_geo[1]     = f.variables['neutral_geographic_velocity2'][:]
      self.velocity_geo[2]     = f.variables['neutral_geographic_velocity3'][:]
    except:
      pass

class IPE:
  def __init__(self, grid_filename):
    self.grid = Grid(grid_filename)

  def read_h5(self, h5_filename):
    self.plasma  = Plasma(h5_filename,  self.grid.nlp, self.grid.nmp, self.grid.nfluxtube)
    self.neutral = Neutral(h5_filename, self.grid.nlp, self.grid.nmp, self.grid.nfluxtube)

  def write_netcdf(self, netcdf_filename, time_str):
    # Open
    with Dataset(netcdf_filename, 'w') as o:
      # Attrs
      o.model_name = "IPE"

      # Dimensions
      z_dim = o.createDimension('z',  self.grid.nheights_geo)

      y_dim = o.createDimension('lat',  self.grid.nlat_geo)

      x_dim = o.createDimension('lon', self.grid.nlon_geo)

      time_dim = o.createDimension('time', None)
      time_out = o.createVariable('time', np.float64, ('time',))
      time_out.units = 's'
      time_out.long_name = 'Seconds Since Jan 1, 1965 00 UT'
      t = datetime.strptime(time_str, '%Y%m%d%H%M')
      dt_sec = (t - datetime(1965,1,1)).total_seconds()
      time_out[0] = dt_sec

      # Modify these to provide 3D data to be consistent with
      # GITM / Aether results
      z_var = o.createVariable('z',  'f4', ('lon','lat','z'))
      z_var.long_name = 'Altitude'
      z_var.units     = 'km'

      y_var = o.createVariable('lat', 'f4', ('lon','lat','z'))
      y_var.long_name = 'Latitude'
      y_var.units     = 'degrees_north'

      x_var = o.createVariable('lon', 'f4', ('lon','lat','z'))
      x_var.long_name = 'Longitude'
      x_var.units     = 'degrees_east'

      # Variables
      e_var   = o.createVariable('e-', 'f4', ('lon','lat','z'))
      e_var.long_name = "electron number density"
      e_var.units     = "m^{-3}"

      op_var   = o.createVariable('o_plus', 'f4', ('lon','lat','z'))
      op_var.long_name = "O+ number density"
      op_var.units     = "m^{-3}"
      
      hp_var   = o.createVariable('h_plus',               'f4', ('lon','lat','z'))
      hp_var.long_name = "H+ number density"
      hp_var.units     = "m^{-3}"

      hep_var  = o.createVariable('he_plus',              'f4', ('lon','lat','z'))
      hep_var.long_name = "He+ number density"
      hep_var.units     = "m^{-3}"

      np_var   = o.createVariable('n_plus',               'f4', ('lon','lat','z'))
      np_var.long_name = "N+ number density"
      np_var.units     = "m^{-3}"

      nop_var  = o.createVariable('no_plus',              'f4', ('lon','lat','z'))
      nop_var.long_name = "NO+ number density"
      nop_var.units     = "m^{-3}"

      o2p_var  = o.createVariable('o2_plus',              'f4', ('lon','lat','z'))
      o2p_var.long_name = "O2+ number density"
      o2p_var.units     = "m^{-3}"

      n2p_var  = o.createVariable('n2_plus',              'f4', ('lon','lat','z'))
      n2p_var.long_name = "N2+ number density"
      n2p_var.units     = "m^{-3}"

      op2d_var = o.createVariable('o_plus_2d',            'f4', ('lon','lat','z'))
      op2d_var.long_name = "O+(2D) number density"
      op2d_var.units     = "m^{-3}"

      op2p_var = o.createVariable('o_plus_2p',            'f4', ('lon','lat','z'))
      op2p_var.long_name = "O+(2P) number density"
      op2p_var.units     = "m^{-3}"

      he_var   = o.createVariable('helium',               'f4', ('lon','lat','z'))
      he_var.long_name = "Neutral He density"
      he_var.units     = "kg m^{-3}"

      o_var    = o.createVariable('oxygen',               'f4', ('lon','lat','z'))
      o_var.long_name = "Neutral O density"
      o_var.units     = "kg m^{-3}"

      o2_var   = o.createVariable('molecular_oxygen',     'f4', ('lon','lat','z'))
      o2_var.long_name = "Neutral O2 density"
      o2_var.units     = "kg m^{-3}"

      n2_var   = o.createVariable('molecular_nitrogen',   'f4', ('lon','lat','z'))
      n2_var.long_name = "Neutral N2 density"
      n2_var.units     = "kg m^{-3}"

      n_var    = o.createVariable('nitrogen',             'f4', ('lon','lat','z'))
      n_var.long_name = "Neutral N density"
      n_var.units     = "kg m^{-3}"

      h_var    = o.createVariable('hydrogen',             'f4', ('lon','lat','z'))
      h_var.long_name = "Neutral H density"
      h_var.units     = "kg m^{-3}"

      t_var    = o.createVariable('temperature',          'f4', ('lon','lat','z'))
      t_var.long_name = "Neutral temperature"
      t_var.units     = "K"

      ua_var    = o.createVariable('u_apex',               'f4', ('lon','lat','z'))
      ua_var.long_name = "Apex1 Velocity"
      ua_var.units     = "m s^{-1}"

      va_var    = o.createVariable('v_apex',               'f4', ('lon','lat','z'))
      va_var.long_name = "Apex2 Velocity"
      va_var.units     = "m s^{-1}"

      wa_var    = o.createVariable('w_apex',               'f4', ('lon','lat','z'))
      wa_var.long_name = "Apex3 Velocity"
      wa_var.units     = "m s^{-1}"

      ug_var    = o.createVariable('u_geo',                'f4', ('lon','lat','z'))
      ug_var.long_name = "Geographic Velocity1"
      ug_var.units     = "m s^{-1}"

      vg_var    = o.createVariable('v_geo',                'f4', ('lon','lat','z'))
      vg_var.long_name = "Geographic Velocity2"
      vg_var.units     = "m s^{-1}"

      wg_var    = o.createVariable('w_geo',                'f4', ('lon','lat','z'))
      wg_var.long_name = "Geographic Velocity3"
      wg_var.units     = "m s^{-1}"

      it_var   = o.createVariable('ion_temperature',      'f4', ('lon','lat','z'))
      it_var.long_name = "Ion temperature"
      it_var.units     = "K"

      et_var   = o.createVariable('electron_temperature', 'f4', ('lon','lat','z'))
      et_var.long_name = "Electron temperature"
      et_var.units     = "K"

      nLons = len(self.grid.longitude_geo)
      nLats = len(self.grid.latitude_geo)
      nAlts = len(self.grid.altitude_geo)

      lons3d = np.zeros((nLons, nLats, nAlts))
      lats3d = np.zeros((nLons, nLats, nAlts))
      alts3d = np.zeros((nLons, nLats, nAlts))
      electron = np.zeros((nLons, nLats, nAlts))

      for iLon in range(nLons):
        for iLat in range(nLats):
          alts3d[iLon, iLat, :] = self.grid.altitude_geo * 1000.0
      for iLon in range(nLons):
        for iAlt in range(nAlts):
          lats3d[iLon, :, iAlt] = self.grid.latitude_geo
      for iLat in range(nLats):
        for iAlt in range(nAlts):
          lons3d[:, iLat, iAlt] = self.grid.longitude_geo

      z_var[:] = alts3d
      y_var[:] = lats3d
      x_var[:] = lons3d

      op = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[0])
      op_var[:] = op

      hp = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[1])
      hp_var[:] = hp
      
      hep = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[2])
      hep_var[:] = hep

      n1p   = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[3])
      np_var[:] = n1p

      nop  = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[4])
      nop_var[:] = nop

      o2p  = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[5])
      o2p_var[:] = o2p

      n2p  = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[6])
      n2p_var[:] = n2p

      op2d = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[7])
      op2d_var[:] = op2d

      op2p = self.grid.interpolate_to_geogrid(self.plasma.ion_densities[8])
      op2p_var[:] = op2p

      electron = op + hp 
      e_var[:] = electron

      he_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.helium)
      o_var[:]    = self.grid.interpolate_to_geogrid(self.neutral.oxygen)
      o2_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.molecular_oxygen)
      n2_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.molecular_nitrogen)
      n_var[:]    = self.grid.interpolate_to_geogrid(self.neutral.nitrogen)
      h_var[:]    = self.grid.interpolate_to_geogrid(self.neutral.hydrogen)
      t_var[:]    = self.grid.interpolate_to_geogrid(self.neutral.neutral_temperature)
      ua_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_apex[0])
      va_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_apex[1])
      wa_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_apex[2])
      try:
        ug_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_geo[0])
        vg_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_geo[1])
        wg_var[:]   = self.grid.interpolate_to_geogrid(self.neutral.velocity_geo[2])
      except:
        pass
      it_var[:]   = self.grid.interpolate_to_geogrid(self.plasma.ion_temperature)
      et_var[:]   = self.grid.interpolate_to_geogrid(self.plasma.electron_temperature)

    return

def load_and_write(i):
  print('Reading file : ', files[i])
  timestamp = files[i][-15:-3]
  ipe.read_h5(files[i])
  ipe.write_netcdf(path.join(out_dir,"IPE_Params.geo.{}.nc".format(timestamp)), 
                   timestamp)


## input parsing options
parser = ArgumentParser(description='Interpolate IPE Outputs to a geographic grid',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('-g', '--gridfile', default=None,
                    help='path to IPE_Grid.nc (default is to look in the input directory)')
parser.add_argument('-i', '--indir',  type=str, default="./",
                    help='path to input directory, if different from pwd')
parser.add_argument('-o', '--outdir', default=None,
                    help='path to output directory, if you do not want to write to indir')
parser.add_argument('-keep', action='store_true',
                    help="Include this flag to not delete the raw outputs")
parser.add_argument('-n', '--nprocs', type=int, default=1,
                    help='Number of processors to use.')
args = parser.parse_args()


# Set defaults for outdir & gridfile
out_dir = args.indir if args.outdir is None else args.outdir
grid_file = path.join(args.indir, 'IPE_Grid.nc') if args.gridfile is None else args.gridfile

# Read in grid, find input files
ipe = IPE(grid_file)
files = sorted(glob.glob(path.join(args.indir,"IPE_State.apex.*")))

if args.nprocs > 1:
  p = Pool(min([len(files),args.nprocs]))
  p.map(load_and_write,range(len(files)))
else:
  for iFile in range(len(files)):
    load_and_write(iFile)

# Remove files if we are not told to -keep them
#if not args.keep:
#  for eachFile in files:
#    remove(eachFile)
