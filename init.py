import os, requests, io, zipfile, argparse
from simpledbf import Dbf5


def main(path):
    if not os.path.exists(path):
        # make the directory, but only if the root path exists (e.g., if '/efs' exists)
        if os.path.exists(os.path.abspath(path.split('/')[0])):
            os.makedirs(path)
        else:
            print('Root path does not exist.')
            return

    # get HydroSHEDS direction grids
    outpath = os.path.join(path, 'hydrosheds')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    # for region in ['af', 'as', 'au', 'ca', 'eu', 'na', 'sa']:
    for region in ['au']:
        print('Downloading HydroSHEDS for {}'.format(region))
        for grid in ['dir', 'acc']:
            response = requests.get(
                'https://s3-us-west-2.amazonaws.com/cuencas/hydrosheds/{}_{}_15s_bil.zip'.format(region, grid))
            file = io.BytesIO(response.content)
            zf = zipfile.ZipFile(file)
            members = [n for n in zf.namelist() if n[-4:] not in ['.htm', '.pdf']]
            zf.extractall(outpath, members)

    # get HydroBASINS shapefiles
    outpath = os.path.join(path, 'hydrobasins')
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    # for region in ['af', 'ar', 'as', 'au', 'eu', 'na', 'sa', 'si']:
    for region in ['au']:
        print('Processing HydroBASINS for {}'.format(region))
        h5path = os.path.join(outpath, 'hybas_{}_v1c.h5'.format(region))
        if os.path.exists(h5path):
            os.remove(h5path)
        for level in ['00', '01-06', '07', '08', '09']:
            base = 'hybas_{}_lev{}_v1c'.format(region, level)
            url = 'https://s3-us-west-2.amazonaws.com/cuencas/hydrobasins/{}.zip'.format(base)
            response = requests.get(url)
            file = io.BytesIO(response.content)
            zf = zipfile.ZipFile(file)
            members = [n for n in zf.namelist() if n[-4:] not in ['.htm', '.pdf']]
            zf.extractall(outpath, members)

            if level == '00':
                dbf = Dbf5(os.path.join(outpath, base + '.dbf'))
                dbf.to_pandashdf(h5path, table='level' + level)

    print('Finished')
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', default=os.environ.get('CUENCAS_PATH', './data'),
                        help='''Path (local) or region (efs)''')
    args = parser.parse_args()

    main(args.path)
