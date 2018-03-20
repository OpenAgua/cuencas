import geopandas as gpd
import os

from osgeo import gdal
from shapely.ops import cascaded_union
from shapely.geometry import mapping, JOIN_STYLE

from .basin_search import delineate_from_basins
from .grid_search import delineate_missing_from_grid
from .utils import get_grid_region, get_region01, get_delineation_mode


def delineate(rootpath=None, point=None, max_level=7, cell_size=15, omit_sinks=True, feature_type='Feature',
              flavor='geojson',
              buffer_eps=0.0025, mode='traditional'):
    """Core delineation routine. Point should be as in GeoJSON: [lng, lat]"""

    # STEP 1: Intialization

    # register the bil driver
    bildriver = gdal.GetDriverByName('EHdr')
    bildriver.Register()

    # register the geotiff driver
    geodriver = gdal.GetDriverByName('GTiff')
    geodriver.Register()

    dirpath = os.path.join(rootpath, 'hydrosheds', '{}_dir_{}s.bil')
    accpath = os.path.join(rootpath, 'hydrosheds', '{}_acc_{}s.bil')

    grid_region = get_grid_region(point, dirpath, cell_size=cell_size)
    PATH = os.path.join(rootpath, 'hydrobasins', 'hybas_{r}_lev{l:02}_v1c.{e}')
    region01 = get_region01(PATH, point)

    lng, lat = point

    hydrobasins = {}
    feature0x = None
    remnant = None
    for i, level in enumerate(range(max_level, 0, -1)):
        path = PATH.format(r=region01, l=level, e='shp')
        basins = gpd.read_file(path)
        if i == 0:
            feature0x = basins.cx[lng - 0.001:lng + 0.001, lat - 0.001:lat + 0.001]

            props0x = feature0x.iloc[0]
            remnant = props0x['geometry']

            mode = get_delineation_mode(accpath, point, basins, props0x, grid_region, cell_size)

            if mode == 'traditional':
                break

        hydrobasins[level] = basins

    # STEP 3: Delineate from HydroBASINS

    if mode == 'hybrid':
        hydropath = PATH
        h5path = os.path.join(rootpath, 'hydrobasins', 'hybas_{}_v1c.h5'.format(region01))
        main = delineate_from_basins(hydropath, h5path, point, hydrobasins, region01, feature0x, max_level, omit_sinks)
    else:
        main = None
        remnant = None

    # STEP 4: Delineate from HydroSHEDS flow direction grid

    remaining = delineate_missing_from_grid(point, grid_region, dirpath, geodriver, cell_size, mask=remnant)

    basin = main
    if remaining:
        simplified = remaining.simplify(0.0041)
        # simplified = remaining
    else:
        simplified = None
    if main and simplified:
        basin = cascaded_union([main, simplified])
    elif simplified:
        basin = simplified
    if simplified:
        # we need to cleanup slivers created on join
        # method from: https://gis.stackexchange.com/questions/120286/removing-small-polygons-gaps-in-a-shapely-polygon
        eps = 0.005
        basin = basin.buffer(eps, 1, join_style=JOIN_STYLE.mitre).buffer(-eps, 1, join_style=JOIN_STYLE.mitre)


    if flavor == 'geojson':
        # coordinates = [mapping(basin.exterior)['coordinates']]
        coordinates = mapping(basin)['coordinates']
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': coordinates
            },
            'properties': {}
        }
        if feature_type == 'Feature':
            return feature
        else:
            return {
                'type': 'FeatureCollection',
                'features': [feature],
                'properties': {}
            }

    else:
        return basin
