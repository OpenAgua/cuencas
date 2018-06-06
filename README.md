# rapid-watershed-delineation

* This is a brand new effort to create a publicly accessible web API to rapidly delineate a watershed in most parts of the world.
* This is in progress. No actual API endpoint exists yet.
* The tool uses both traditional and hybrid delineation methods. Both techniques rely on [HydroSHEDS](http://www.hydrosheds.org/). The hybrid method searches [HydroBASINS](http://www.hydrosheds.org/page/hydrobasins), then fills in missing areas with traditional delineation using the HydroSHEDS flow direction dataset (15 arc-seconds). The hybrid method is used for mainstem rivers. In non-mainstem basins, the traditional delineation method alone is used. Determining which method to use is a critical peice of the algorithmic magic underpinning this tool.
* Detailed documentation forthcoming.

## Worker setup

0. RabbitMQ

```
docker pull rabbitmq
```