from pydantic import BaseModel
import pydantic_geojson as pg
from enum import Enum
from lu_igi.models.land_use import LandUse

class Profile(Enum):
  RESIDENTIAL_INDIVIDUAL = 'Жилая застройка - ИЖС'
  RESIDENTIAL_LOWRISE = 'Жилая застройка - Малоэтажная'
  RESIDENTIAL_MIDRISE = 'Жилая застройка - Среднеэтажная'
  RESIDENTIAL_MULTISTOREY = 'Жилая застройка - Многоэтажная'
  BUSINESS = 'Общественно-деловая'
  RECREATION = 'Рекреационная'
  SPECIAL = 'Специального назначения'
  INDUSTRIAL = 'Промышленная'
  AGRICULTURE = 'Сельско-хозяйственная'
  TRANSPORT = 'Транспортная инженерная'

class BlocksFeatureCollection(pg.FeatureCollectionModel):

    class BlocksFeature(pg.FeatureModel):

        class BlocksProperties(BaseModel):
            ...

        geometry : pg.PolygonModel
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
            land_use : str
            assigned_land_use : str

        geometry : pg.PolygonModel
        properties : LandUseProperties

    features : list[LandUseFeature]

class LandUseResponseItem(BaseModel):
    blocks : LandUseFeatureCollection
    fitness : dict[str, float]
