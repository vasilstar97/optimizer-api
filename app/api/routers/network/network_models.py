from pydantic import BaseModel
import pydantic_geojson as pg

class RoadNetworkModel(pg.FeatureCollectionModel):

    class RoadNetworkFeature(pg.FeatureModel):
        geometry : pg.LineStringModel | pg.MultiLineStringModel
        # properties : dict

    features : list[RoadNetworkFeature]