from osgeo import gdal
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import cascaded_union

from rasterio import features
from rasterio.transform import from_origin

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


def delineate_missing_from_grid(point, region, dirpath, geodriver, cell_size, mask=None):

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
    array = np.zeros((rows, cols), dtype=np.dtype('uint8'))

    for (x, y), val in catchments.items():
        array[y - ymin, x - xmin] = val

    # define raster origin
    originLon, originLat = xy2lonlat(xmin, ymin, gt)
    cellWidth = cellHeight = cell_size / 60 / 60

    # create the shapes
    transform = from_origin(originLon, originLat, cellWidth, cellHeight)
    mask = array != 0
    shapes = features.shapes(array, mask=mask, transform=transform)

    # there may be more than one main feature
    polygons = []
    for shape, i in shapes:
        polygons.extend([Polygon(coords) for coords in shape['coordinates']])
    polygon = cascaded_union(polygons)

    return polygon
