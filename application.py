#!flask/bin/python
import os
from flask import Flask, request, jsonify
from delineation.delineate import delineate

application = Flask(__name__)
application.config['BASEPATH'] = os.environ.get('CUENCAS_PATH', './data')  # e.g., '/efs/hydrodata'


@application.route('/')
def index():
    return 'Hello, hydrologist!'


@application.route('/api/delineate_point', methods=['GET', 'POST'])
def delineate_point_api():
    """
    Delineate a single point.
    """
    lat = request.args.get('lat', type=float) or request.json.get('lat')
    lon = request.args.get('lon', type=float) or request.json.get('lon')
    cellsize = request.args.get('cellsize', 15, type=float) or request.json.get('cellsize', 15)
    feature_type = request.args.get('type', 'Feature') or request.json.get('type', 'Feature')

    if lat is None or lon is None:
        return 'Oops! Did you forget a lat or lon?'

    else:
        rootpath = application.config['BASEPATH']
        geojson = delineate(rootpath, point=(lon, lat), cell_size=cellsize, feature_type=feature_type, flavor='geojson')
        return jsonify(geojson)


if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080, debug=True)
