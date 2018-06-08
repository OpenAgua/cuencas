FROM ubuntu:16.04
MAINTAINER David Rheinheimer "drheinheimer@umass.edu"

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

RUN apt-get install -y software-properties-common
RUN apt-add-repository ppa:ubuntugis/ppa \
  && apt-get update \
  && apt-get install -y gdal-bin python3-gdal python3-numpy libgdal-dev

RUN pip3 install --no-cache-dir rasterio pandas fiona shapely geopandas kml2geojson simpledbf numexpr tables
RUN pip3 install --no-cache-dir gunicorn celery pymongo flask requests

# bundle app source
COPY . /app
WORKDIR /app