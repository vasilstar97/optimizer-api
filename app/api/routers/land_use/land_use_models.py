from pydantic import BaseModel
import pydantic_geojson as pg
from enum import Enum

class RoadsFeatureCollection(pg.FeatureCollectionModel):

    class RoadsFeature(pg.FeatureModel):
        geometry : pg.LineStringModel | pg.MultiLineStringModel
        properties : dict = {}

    features : list[RoadsFeature]  

class BlocksFeatureCollection(pg.FeatureCollectionModel):

    class BlocksFeature(pg.FeatureModel):

        class BlocksProperties(BaseModel):
            ...

        geometry : pg.PolygonModel | pg.MultiPolygonModel
        properties : BlocksProperties

    features : list[BlocksFeature]

class ZonesFeatureCollection(pg.FeatureCollectionModel):

    class ZonesFeature(pg.FeatureModel):

        class ZonesProperties(BaseModel):

            class FunctionalZoneType(BaseModel):
                id : int
                name : str
                nickname : str

            functional_zone_type : FunctionalZoneType

        geometry : pg.PolygonModel | pg.MultiPolygonModel
        properties : ZonesProperties

    features : list[ZonesFeature]

class LandUseFeatureCollection(pg.FeatureCollectionModel):

    class LandUseFeature(pg.FeatureModel):

        class LandUseProperties(BaseModel):
            land_use : str | None
            assigned_land_use : str

        geometry : pg.PolygonModel
        properties : LandUseProperties

    features : list[LandUseFeature]

class LandUseResponseItem(BaseModel):
    blocks : LandUseFeatureCollection
    fitness : dict[str, float]
