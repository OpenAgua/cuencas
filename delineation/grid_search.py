import os, tempfile, json
from osgeo import gdal, ogr
import numpy as np
from gdalconst import GDT_Int32
import kml2geojson
from shapely.geometry import Point, Polygon
from shapely.ops import cascaded_union

# Install GDAL using:
# pip install gdal --global-option=build_ext --global-option="-I/usr/include/gdal/"

from .utils import lonlat2xy, xy2lonlat

contributions = {
    (0, 0): 2,
    (0, 1): 4,
    (0, 2): 8,
    (1, 0): 1,
    (1, 1): 0,
    (1, 2): 16,
    (2, 0): 128,
    (2, 1): 64,
    (2, 2): 32
}

offset = {
    0: (0, 0),
    1: (1, 0),
    2: (1, -1),
    4: (0, -1),
    8: (-1, -1),
    16: (-1, 0),
    32: (-1, 1),
    64: (0, 1),
    128: (1, 1),
}


def delineate_missing_from_grid(point, region, dirpath, geodriver, cell_size, mask=None):

    with tempfile.TemporaryDirectory() as tmpdir:

        src = {}

        # this is critically important: catchment entries represent points that are in the catchment to be returned
        catchments = {}

        # initialize pour point
        lon, lat = point

        fdir = None

        bil = gdal.Open(dirpath.format(region, cell_size))
        gt = bil.GetGeoTransform()
        fdir = bil.GetRasterBand(1)
        x, y = lonlat2xy(lon, lat, gt)

        # the core routine to find the catchment
        def add_to_catchment(x, y, xt, yt, val=1, depth=0, overlap=0):
            area = fdir.ReadAsArray(x - 1, y - 1, 3, 3)  # does not account for edge cases yet

            catchments[(xt, yt)] = val

            if overlap or depth == 950:
                return

            for i in range(3):  # rows
                for j in range(3):  # columns
                    if area[i, j] == contributions[(i, j)]:
                        xnew = x + (j - 1)
                        ynew = y + (i - 1)
                        xtnew = xt + (j - 1)
                        ytnew = yt + (i - 1)

                        # need to update region here based on xnew, ynew
                        # in the meantime, just assume the region is the same
                        if (xtnew, ytnew) not in catchments:
                            lonnew, latnew = xy2lonlat(xtnew, ytnew, gt)
                            if not mask or mask.contains(Point(lonnew, latnew)):
                                add_to_catchment(xnew, ynew, xtnew, ytnew, val, depth=depth + 1)

        # update catchments
        try:
            add_to_catchment(x, y, xt=x, yt=y)
        except:
            return None

        # create numpy array
        xmin = min([x for (x, y) in catchments])
        xmax = max([x for (x, y) in catchments])
        ymin = min([y for (x, y) in catchments])
        ymax = max([y for (x, y) in catchments])

        # get the cols & rows
        cols = xmax - xmin + 1
        rows = ymax - ymin + 1
        array = np.zeros((rows, cols))

        for (x, y), val in catchments.items():
            array[y - ymin, x - xmin] = val

        # define raster origin
        originLon, originLat = xy2lonlat(xmin, ymin, gt)
        cellWidth = cellHeight = cell_size / 60 / 60

        layername = 'catchments'

        # create catchments raster
        tmptifpath = os.path.join(tmpdir, 'out.tif')
        geotiff = geodriver.Create(tmptifpath, cols, rows, 1, GDT_Int32)
        geotiff.SetGeoTransform((originLon, cellWidth, 0, originLat, 0, -cellHeight))
        geoband = geotiff.GetRasterBand(1)
        geoband.WriteArray(array)

        # prepare output vector (kml) layer
        # NB: GDAL's GeoJSON output is not formatted correctly. So the hack here
        # is to output to kml, then convert to geojson using the kml2geojson module.
        # driver = ogr.GetDriverByName('GeoJSON')
        # tmppath = os.path.join(tmpdir, layername + '.geojson')
        driver = ogr.GetDriverByName('KML')
        tmppath = os.path.join(tmpdir, layername + '.kml')
        tmpsrc = driver.CreateDataSource(tmppath)
        tmplayer = tmpsrc.CreateLayer(layername, srs=None)

        # add field
        subwatid = ogr.FieldDefn('id', ogr.OFTInteger)
        tmplayer.CreateField(subwatid)

        # The "2" here indicates to write the GeoTIFF values to the "id" column.
        # Other options are 1: "name" column and 2: "description" column
        gdal.Polygonize(geoband, None, tmplayer, 2, [], callback=None)

        # geotiff.FlushCache()
        del geoband
        del geotiff
        del tmpsrc
        del tmplayer

        kml2geojson.main.convert(tmppath, tmpdir)
        with open(tmppath.replace('.kml', '.geojson')) as f:
            gj = json.loads(f.read())
            features = [f for f in gj['features'] if f['properties']['id'] != '0']

    polygon = None
    if features:
        # there may be more than one main feature
        polygons = [Polygon(f['geometry']['coordinates'][0]) for f in features]
        polygon = cascaded_union(polygons)

    return polygon
