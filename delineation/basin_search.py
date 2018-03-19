import fiona
import pandas as pd
from shapely.ops import cascaded_union
from time import time
from matplotlib.path import Path
from osgeo import ogr


def point_in_polygon(polygon, point):
    if type(polygon[0][0]) == float:
        path = Path(polygon, closed=True)
        if path.contains_point(point):
            return True
    else:
        for subpolygon in polygon:
            if point_in_polygon(subpolygon, point):
                return True


def point_in_feature(feature, point):
    polygon = feature['geometry']['coordinates']
    return point_in_polygon(polygon, point)


def get_feature00(path, point, PFAF_X, PFAF_X_ID):
    with fiona.open(path) as shapes:
        for feature in shapes:
            if feature['properties'][PFAF_X] != PFAF_X_ID:
                continue
            if point_in_feature(feature, point):
                return feature


def get_feature00_test(path, point, PFAF_X, PFAF_X_ID):
    # Get the input Layer
    inShapefile = path
    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(inShapefile, 0)
    inLayer = inDataSource.GetLayer()
    return inLayer

    # with fiona.open(path) as shapes:
    #     for feature in shapes:
    #         if feature['properties'][PFAF_X] != PFAF_X_ID:
    #             continue
    #         if point_in_feature(feature, point):
    #             feature00 = feature
    #             break
    #


def get_basins(df00, hydrobasins, props00, max_level, omit_sinks=True):
    # NOTE: This only works for subwats in the main stem. To search side subwats,
    # an additional search of the original df00 needs to be performed to omit
    # higher level subwats that don't contribute to the smallest subat

    all_basins = []
    df00x = df00.iloc[:]
    # start_time = time()
    for level in range(2, max_level + 1):
        PFAFp = 'PFAF_{}'.format(level - 1)
        PFAF = 'PFAF_{}'.format(level)

        # print(PFAF)
        df00x = df00x.loc[df00x[PFAFp] == props00[PFAFp]]  # filter to include only PFAFs of interest

        PFAFlist = list(set(df00x[PFAF].tolist()))  # list of current level PFAFs

        #         print('loading dataset: %s' % (time() - start_time))
        basins = hydrobasins[level]
        #         print('loaded dataset: %s' % (time() - start_time))
        basins = basins.loc[basins['PFAF_ID'].isin(PFAFlist)]  # initial filter to current PFAF

        # filter out lower basins; this basically follows a drop of water downslope
        # if a subbasin contributes to the current basin, then include it (and filter it out from future searchs)
        this_basin = basins.loc[basins['PFAF_ID'] == props00[PFAF]]
        this_basin_id = this_basin.iloc[0]['HYBAS_ID']
        to_include = []
        PFAF_IDs = []  # for filtering df00 so we don't query this region next time
        #         print('starting subbasin search: %s' % (time() - start_time))
        for i, subbasin in basins.iterrows():
            if omit_sinks:
                next_down = subbasin['NEXT_DOWN']
            next_sink = subbasin['NEXT_SINK']
            main_basin = subbasin['MAIN_BAS']
            if omit_sinks and main_basin != next_sink:
                PFAF_IDs.append(subbasin['PFAF_ID'])
                continue
            subbasin_chain = [subbasin['HYBAS_ID']]
            PFAF_chain = [subbasin['PFAF_ID']]
            if subbasin['HYBAS_ID'] in to_include:
                continue
            while next_down:
                if next_down == this_basin_id or next_down in to_include:
                    to_include.extend(subbasin_chain)
                    PFAF_IDs.extend(PFAF_chain)
                    break

                down_basin = basins.loc[basins['HYBAS_ID'] == next_down]
                if not down_basin.empty:
                    down_basin_props = down_basin.iloc[0]
                    subbasin_chain.append(down_basin_props['HYBAS_ID'])
                    PFAF_chain.append(down_basin_props['PFAF_ID'])
                    if omit_sinks:
                        next_down = down_basin_props['NEXT_DOWN']
                    else:
                        next_down = down_basin_props['NEXT_SINK']
                else:
                    break  # it's unclear how we could get here
        #         print('finished subbasin search: %s' % (time() - start_time))
        to_include_set = set(to_include)
        basins = basins.loc[basins['HYBAS_ID'].isin(to_include_set)]
        # basins['OA_ID'] = OA_ID
        # basins['NAME'] = OA_NAME
        #         print('merging with all_basins: %s' % (time() - start_time))
        if not basins.empty:
            all_basins.append(basins)
        #         print('finished merge: %s' % (time() - start_time))

        df00x = df00x.loc[~df00x[PFAF].isin(PFAF_IDs)]  # filter out this region
    # print('search time: %s' % (time() - start_time))

    return all_basins


def get_basins_flat(df00, hydrobasins, props00, max_level, omit_sinks=True):
    # NOTE: This only works for subwats in the main stem. To search side subwats,
    # an additional search of the original df00 needs to be performed to omit
    # higher level subwats that don't contribute to the smallest subat

    all_basins = []
    df00x = df00.iloc[:]
    # start_time = time()
    for level in range(2, max_level + 1):
        PFAFp = 'PFAF_{}'.format(level - 1)
        PFAF = 'PFAF_{}'.format(level)

        # print(PFAF)
        df00x = df00x.loc[df00x[PFAFp] == props00[PFAFp]]  # filter to include only PFAFs of interest

        PFAFlist = list(set(df00x[PFAF].tolist()))  # list of current level PFAFs

        #         print('loading dataset: %s' % (time() - start_time))
        basins = hydrobasins[level]
        #         print('loaded dataset: %s' % (time() - start_time))
        basins = basins.loc[basins['PFAF_ID'].isin(PFAFlist)]  # initial filter to current PFAF

        # filter out lower basins; this basically follows a drop of water downslope
        # if a subbasin contributes to the current basin, then include it (and filter it out from future searchs)
        this_basin = basins.loc[basins['PFAF_ID'] == props00[PFAF]]
        this_basin_id = this_basin.iloc[0]['HYBAS_ID']
        to_include = []
        PFAF_IDs = []  # for filtering df00 so we don't query this region next time
        #         print('starting subbasin search: %s' % (time() - start_time))
        for i, subbasin in basins.iterrows():
            if omit_sinks:
                next_down = subbasin['NEXT_DOWN']
            next_sink = subbasin['NEXT_SINK']
            main_basin = subbasin['MAIN_BAS']
            if omit_sinks and main_basin != next_sink:
                PFAF_IDs.append(subbasin['PFAF_ID'])
                continue
            subbasin_chain = [subbasin['HYBAS_ID']]
            PFAF_chain = [subbasin['PFAF_ID']]
            if subbasin['HYBAS_ID'] in to_include:
                continue
            while next_down:
                if next_down == this_basin_id or next_down in to_include:
                    to_include.extend(subbasin_chain)
                    PFAF_IDs.extend(PFAF_chain)
                    break

                down_basin = basins.loc[basins['HYBAS_ID'] == next_down]
                if not down_basin.empty:
                    down_basin_props = down_basin.iloc[0]
                    subbasin_chain.append(down_basin_props['HYBAS_ID'])
                    PFAF_chain.append(down_basin_props['PFAF_ID'])
                    if omit_sinks:
                        next_down = down_basin_props['NEXT_DOWN']
                    else:
                        next_down = down_basin_props['NEXT_SINK']
                else:
                    break  # it's unclear how we could get here
        #         print('finished subbasin search: %s' % (time() - start_time))
        to_include_set = set(to_include)
        basins = basins.loc[basins['HYBAS_ID'].isin(to_include_set)]
        # basins['OA_ID'] = OA_ID
        # basins['NAME'] = OA_NAME
        #         print('merging with all_basins: %s' % (time() - start_time))
        if not basins.empty:
            all_basins.append(basins)
        #         print('finished merge: %s' % (time() - start_time))

        df00x = df00x.loc[~df00x[PFAF].isin(PFAF_IDs)]  # filter out this region
    # print('search time: %s' % (time() - start_time))

    return all_basins


def delineate_from_basins(hydropath, h5path, point, hydrobasins, region01, feature0x, max_level=7, omit_sinks=True):
    start_time = time()

    path01 = hydropath.format(r=region01, l=0, e='shp')
    PFAF_X = 'PFAF_{}'.format(max_level)
    PFAF_X_ID = feature0x.iloc[0]['PFAF_ID']

    feature00 = get_feature00(path01, point, PFAF_X, PFAF_X_ID)
    print('found PFAF 12 feature: %s' % (time() - start_time))

    if feature00 is None:
        return None, None

    props00 = feature00['properties']
    # print('found PFAF 12 feature: %s' % (time() - start_time))

    # load the level00 lookup table
    df00 = pd.read_hdf(h5path, 'level00')
    print('loaded level 00 lookup table: %s' % (time() - start_time))

    df00x = df00.loc[df00['MAIN_BAS'] == props00['MAIN_BAS']]
    print('filtered continent to basin: %s' % (time() - start_time))

    all_basins = get_basins(df00x, hydrobasins, props00, max_level, omit_sinks)
    # all_basins = get_basins_flat(df00x, hydrobasins, props00, max_level, omit_sinks)
    print('found basins: %s' % (time() - start_time))

    basin = None
    polygons = []

    if all_basins:
        for basins in all_basins:
            polygons.extend(row['geometry'] for i, row in basins.iterrows())

    if polygons:
        basin = cascaded_union(polygons)

    return basin
