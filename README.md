# catchment-delineation

## Some caveats

* For now, there is no documentation for this API. If the API eventually becomes robust enough and popular enough, we might make it a bit more formal.
* We might also restrict/control access in the future. For now, anybody can use it (definitely not a limitation!), though if you do use it please use it gently, as it’s currently paid for by the author.
* Larger catchments won’t be delineated. This is due to the amount of time it takes to delineate larger catchments: http requests time out after a while. You've seen this when loading a page and the page doesn’t respond quickly: you get a timeout error in your browser. Same thing here. We need to figure out a way to improve the efficiency, perhaps by leveraging Google Earth Engine. Until then, smaller catchments only.
* An algorithm for catchments that span the underlying datasets have not been developed.
* Asia is not currently included.
