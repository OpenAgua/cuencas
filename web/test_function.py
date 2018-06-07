from time import time
import json
import os

from descartes import PolygonPatch
import matplotlib.pyplot as plt

from delineation.delineation import delineate


def run_test():
    # lat, lng = -33.982, 115.765 # Australia
    # lat, lng = 30.01857, 31.21864  # Nile @ Cairo
    # lat, lng = 3.5856, 32.03533 # White Nile @ Uganda
    # lat, lng = -0.09742, 29.59311 # Uganda - Ishango
    lat, lng = 37.91864, -119.65922 # HH
    # lat, lng = 32.49434, -114.81376  # Colorado River at San Luis Rio Colorado
    # lat, lng = 32.52726, -114.79777  # Colorado River tributary above San Luis Rio Colorado
    # lat, lng = 29.95262, -90.06059 # Mississippi NOLA @ French Quarter
    # lat, lng = 25.70192, -99.27689
    point = (lng, lat)

    # flavor = 'geojson'
    flavor = 'shape'

    start_time = time()
    basin = delineate(rootpath='./data', point=point, max_level=7, flavor=flavor, omit_sinks=True)
    print('Total time: {} seconds'.format(time() - start_time))

    if basin:
        if flavor == 'geojson':
            fname = 'test.geojson'
            if os.path.exists(fname):
                os.remove(fname)
            with open(fname, 'w') as f:
                f.write(json.dumps(basin))
        else:
            fig, ax = plt.subplots(figsize=(10, 10), dpi=96)
            ax.add_patch(PolygonPatch(basin))
            ax.axis('scaled')
            ax.plot([lng], [lat], marker='o', markersize=3, color="red")
            plt.show()
    else:
        print('no basin found')


if __name__ == '__main__':
    run_test()
