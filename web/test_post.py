import requests

# from descartes import PolygonPatch
# import matplotlib.pyplot as plt


def run_test():
    lat, lng = 32.49434, -114.81376  # Colorado River at San Luis Rio Colorado
    # lat, lng = 32.52726, -114.79777  # Colorado River tributary above San Luis Rio Colorado
    print((lat, lng))
    resp = requests.post('http://0.0.0.0:8000/delineate_catchment', json={'lat': lat, 'lon': lng})

    content = resp.content.decode()
    print(content)

    # if basin:
    #     fig, ax = plt.subplots(figsize=(10, 10), dpi=96)
    #     ax.add_patch(PolygonPatch(basin))
    #     ax.axis('scaled')
    #     ax.plot([lng], [lat], marker='o', markersize=3, color="red")
    #     plt.show()
    # else:
    #     print('no basin found')


if __name__ == '__main__':
    run_test()
