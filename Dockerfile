FROM ubuntu:16.04

# install python
RUN apt-get update -y
RUN apt-get install -y python3 python3-pip

# install requirements (not from requirements.txt)
RUN apt-get install -y software-properties-common
RUN apt-add-repository ppa:ubuntugis/ppa && apt-get update && apt-get install -y gdal-bin python3-gdal

RUN pip3 install gdal --global-option=build_ext --global-option="-I/usr/include/gdal/"
RUN pip3 install numpy pandas
RUN pip3 install fiona shapely geopandas kml2geojson simpledbf
RUN pip3 install flask requests

# for pytables
#RUN apt-get install libhdf5-serial-dev
RUN pip3 install numexpr tables

# bundle app source
ADD . /app
WORKDIR /app

# download HydroSHEDs and HydroBASINS
RUN python3 init.py

EXPOSE 8080

ENTRYPOINT ["python3"]
CMD ["application.py"]