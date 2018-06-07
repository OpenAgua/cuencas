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
    && apt-get install -y gdal-bin python3-gdal python-numpy libgdal-dev

#RUN pip3 install gdal --global-option=build_ext --global-option="-I/usr/include/gdal/"
RUN pip3 install rasterio

RUN pip3 install celery pymongo

RUN pip3 install pandas
RUN pip3 install fiona shapely geopandas kml2geojson simpledbf
RUN pip3 install flask requests
RUN pip3 install numexpr tables

# bundle app source
ADD . /app
WORKDIR /app

VOLUME ["/data"]

EXPOSE 8000

ENTRYPOINT ["python3"]
CMD ["app.py"]