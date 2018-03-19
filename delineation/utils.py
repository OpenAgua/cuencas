import os, tempfile

from osgeo import gdal, ogr
import fiona
from shapely.ops import cascaded_union
from matplotlib.path import Path
import numpy as np


def lonlat2xy(lon, lat, gt):
    """Convert the map coordinates (lon, lat) to grid coordinates (x, y)"""
    x = int((lon - gt[0]) / gt[1])  # x pixel
    y = int((lat - gt[3]) / gt[5])  # y pixel
    return x, y


def xy2lonlat(x, y, gt):
    """Convert grid coordinates (x, y) to map coordinates (lon, lat)"""
    lon = x * gt[1] + gt[0]
    lat = y * gt[5] + gt[3]
    return lon, lat


def find_hydrosheds_region(lat, lon, exclude=None):
    if exclude is True:
        exclude = None
    # find raster
    # TODO: Fix this. This needs to be done very carefully, especially at the edges.
    if 6 < lat < 38 and -118 < lon < -61 and exclude != 'ca':
        region = 'ca'
    elif -56 < lat < 15 and -93 < lon < -32:
        region = 'sa'
    elif 24 < lat < 61 and -138 < lon < -52:
        region = 'na'
    elif 12 < lat < 62 and -14 < lon < 70 and exclude != 'eu':
        region = 'eu'
    elif -35 < lat < 38 and -19 < lon < 55:
        region = 'af'
    elif -12 < lat < 61 and 57 < lon < 180:
        region = 'as'
    elif -56 < lat < -10 and 112 < lon < 180:
        region = 'au'
    else:
        region = None

    return region


def get_grid_region(point, bilpath, cell_size):
    lon, lat = point

    # find the region, flow direction grid, and x, y
    region_is_correct = False
    region = None
    while not region_is_correct or not region:
        region = find_hydrosheds_region(lat, lon, exclude=region)

        # create the gdal flow direction grid from the bil
        bil = gdal.Open(bilpath.format(region, cell_size))
        center = None

        if bil:
            gt = bil.GetGeoTransform()
            fdir = bil.GetRasterBand(1)

            # load initial region of point
            x, y = lonlat2xy(lon, lat, gt)

            center = fdir.ReadAsArray(x, y, 1, 1)

        if center and center[0][0] != 247:
            region_is_correct = True

    return region


def find_hydrobasins_region(PATH, regions, point):
    for region in regions:
        path = PATH.format(r=region, l=1, e='shp')
        with fiona.open(path) as shapes:
            feature = next(iter(shapes))
            polygons = feature['geometry']['coordinates']
            for polygon in polygons:
                for subpolygon in polygon:
                    path = Path(subpolygon, closed=True)
                    if path.contains_point(point):
                        return region


def get_region01(PATH, point):
    regions = ['as', 'af', 'eu', 'na', 'sa', 'au']

    lng, lat = point

    if 90 < lng < 190 and lat < 8:  # prioritize Australia
        regions = ['au', 'as']
    elif 57 < lng < 155 and 7 < lat < 55:  # prioritize Asia
        regions = ['as', 'eu', 'au']
    elif -30 < lng < 55 and lat < 40:  # prioritize Africa
        regions = ['af', 'eu']
    elif -25 < lng < 70 and 12 < lat:  # prioritize Europe
        regions = ['eu', 'af', 'as']
    elif -82 < lng < -34 and lat < 15:
        regions = ['sa', 'na']
    elif -140 < lng < -52 and 7 < lat < 62:
        regions = ['na', 'sa']

    region01 = find_hydrobasins_region(PATH, regions, point)

    return region01


def get_delineation_mode(accpath, point, basins, feature, region, cell_size):
    lng, lat = point

    # routine to find max upstream flow accumulation
    next_ups = basins.loc[basins['NEXT_DOWN'] == feature['HYBAS_ID']]
    next_ups = next_ups.loc[next_ups['NEXT_SINK'] == feature['NEXT_SINK']]

    mode = None

    if next_ups.empty:
        mode = 'traditional'
    else:

        bil = gdal.Open(accpath.format(region, cell_size))
        acc = bil.GetRasterBand(1)
        gt = bil.GetGeoTransform()
        x, y = lonlat2xy(lng, lat, gt)
        point_acc = acc.ReadAsArray(x, y, 1, 1)[0][0]

        max_up_acc = None
        with tempfile.TemporaryDirectory() as tmpdir:
            next_up = cascaded_union([row['geometry'] for i, row in next_ups.iterrows()])
            west, south, east, north = next_up.bounds
            xmin, ymax = lonlat2xy(west, south, gt)
            xmax, ymin = lonlat2xy(east, north, gt)
            cols = xmax - xmin + 1
            rows = ymax - ymin + 1

            # clipped numpy array from shape (next_up)

            # create layer
            driver = ogr.GetDriverByName("ESRI Shapefile")
            tmppath = os.path.join(tmpdir, 'next_up.shp')
            tmpsrc = driver.CreateDataSource(tmppath)
            tmplayer = tmpsrc.CreateLayer('next_up', srs=None, geom_type=ogr.wkbPolygon)
            valField = ogr.FieldDefn("VAL", ogr.OFTInteger)
            tmplayer.CreateField(valField)

            # create the polygon
            poly = ogr.Geometry(ogr.wkbPolygon)
            for i, n in next_ups.iterrows():
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for coord in list(n['geometry'].exterior.coords):
                    ring.AddPoint(coord[0], coord[1])
                poly.AddGeometry(ring)

            # add the polygon
            # Create the feature and set values
            featureDefn = tmplayer.GetLayerDefn()
            feature = ogr.Feature(featureDefn)
            feature.SetGeometry(poly)
            feature.SetField("VAL", 1)
            tmplayer.CreateFeature(feature)

            # rasterize layer
            originLon, originLat = xy2lonlat(xmin, ymin, gt)
            cellWidth = cellHeight = cell_size / 60 / 60
            tmptifpath = os.path.join(tmpdir, 'next_up.tif')
            geotiff = gdal.GetDriverByName('GTiff').Create(tmptifpath, cols, rows, 1, gdal.GDT_Byte)
            geotiff.SetGeoTransform((originLon, cellWidth, 0, originLat, 0, -cellHeight))
            band = geotiff.GetRasterBand(1)
            band.SetNoDataValue(0)
            band.FlushCache()

            gdal.RasterizeLayer(geotiff, [1], tmplayer, options=["ATTRIBUTE=VAL"])

            # clipped numpy array from flow accumulation grid
            acc_area = acc.ReadAsArray(xmin, ymin, cols, rows)  # grid origin is upper left
            acc_area = np.array(acc_area)

            # area defining upstream shape
            next_up_area = band.ReadAsArray()
            next_up_area = np.array(next_up_area)

            # flow accumulation within upstream shape
            up_acc_area = acc_area * next_up_area

            max_up_acc = up_acc_area.max()

        if max_up_acc > point_acc:
            mode = 'traditional'
        else:
            mode = 'hybrid'

    return mode
