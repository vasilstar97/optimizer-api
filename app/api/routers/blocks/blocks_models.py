from pydantic import BaseModel
import pydantic_geojson as pg

road_network_example = {}

class RoadNetworkModel(pg.FeatureCollectionModel):

    class RoadNetworkFeature(pg.FeatureModel):
        geometry : pg.LineStringModel | pg.MultiLineStringModel
        properties : dict = {}

    features : list[RoadNetworkFeature]

class BlocksModel(pg.FeatureCollectionModel):

    class BlocksFeature(pg.FeatureModel):
        geometry : pg.PolygonModel
        properties : dict = {}

    features : list[BlocksFeature]