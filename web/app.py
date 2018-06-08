import os
from flask import Flask, request, Response
from celery import Celery
import hashlib
import requests
from pymongo import MongoClient

from delineation import delineate

app = Flask(__name__)
app.config['BASEPATH'] = os.environ.get('CUENCAS_DATA_PATH', '/data')  # e.g., '/efs/hydrodata'

# create celery worker
app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', 'amqp://rabbitmq:rabbitmq@rabbit:5672')
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

app.config['MONGO_URL'] = os.environ.get('MONGO_URL', 'mongodb://mongo:27017')


@app.route('/')
def _main():
    return 'hello hydrologist!'


@app.route('/delineate_catchment', methods=['POST'])
def delineate_catchment():
    if request.method != 'POST':
        # Expect app/json request
        return Response("", status=415)

    try:
        new = request.json.get('new')
        user_id = request.json.get('user_id')
        source_id = request.json.get('source_id', 1)
        network_id = request.json.get('network_id')
        name = request.json.get('name')
        lat = request.json.get('lat')
        lon = request.json.get('lon')
        feature_type = request.args.get('type', 'Feature') or request.json.get('type', 'Feature')
        dest = request.json.get('dest')
        key = request.json.get('key')

        if lat is None or lon is None:
            return Response('Oops! Did you forget a lat or lon?', status=500)

        else:
            delineate_catchment_async.delay(user_id, source_id, network_id, name, lat, lon, feature_type, new, dest,
                                            key)
            return Response('', status=200)

    except Exception as ex:
        return Response(ex.message, status=500)


@celery.task()
def delineate_catchment_async(user_id, source_id, network_id, name, lat, lon, feature_type, new, dest, key):
    """
    Delineate a single point.
    """

    with app.app_context():

        BASEPATH = os.environ.get('CUENCAS_DATA_PATH', '/data')

        string = '{}_{}_{}'.format(lat, lon, feature_type)

        uuid = hashlib.md5(string.encode()).hexdigest()

        client = MongoClient(app.config['MONGO_URL'])
        delineations = client.cuencasdb.delineations

        delineation = delineations.find_one({'uuid': uuid})

        name = 'Catchment at {}'.format(name or '({:6f}, {:6f})'.format(lat, lon))

        if new or delineation is None:

            # create geojson
            try:
                geojson = delineate(rootpath=BASEPATH, point=(lon, lat), name=name, cell_size=15,
                                    feature_type=feature_type, flavor='geojson')
            except:
                print('failed to delineate!')
                raise

            # save to db
            try:
                delineations.insert_one({'uuid': uuid, 'geojson': geojson})
            except:
                print('failed to save to database!')

        else:

            geojson = delineation.get('geojson')

        # prepare geojson
        geojson['properties']['name'] = name

        # send back to OpenAgua
        try:
            requests.post(url=dest,
                          json={
                              'key': key,
                              'user_id': user_id,
                              'source_id': source_id,
                              'network_id': network_id,
                              'geojson': geojson
                          })
        except:
            print('ERROR: failed to post result to {}'.format(dest))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
