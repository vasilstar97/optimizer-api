from pydantic import BaseModel, Field
from typing import Literal
import pydantic_geojson as pg

class RoadNetworkModel(pg.FeatureCollectionModel):

    class RoadNetworkFeature(pg.FeatureModel):

        class RoadNetworkProperties(BaseModel):
            status : Literal[1,2,3] = Field(default=2)

        geometry : pg.LineStringModel | pg.MultiLineStringModel
        properties : RoadNetworkProperties

    features : list[RoadNetworkFeature]