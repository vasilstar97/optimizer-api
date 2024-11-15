from pydantic import BaseModel
import pydantic_geojson as pg
from enum import Enum

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

class BlocksModel(pg.FeatureCollectionModel):

    class BlocksFeature(pg.FeatureModel):
        geometry : pg.PolygonModel
        properties : dict | None = {}

    features : list[BlocksFeature]

class ZonesModel(pg.FeatureCollectionModel):

    class ZonesFeature(pg.FeatureModel):

        class ZonesProperties(BaseModel):
            land_use : str

        geometry : pg.PolygonModel
        properties : ZonesProperties

    features : list[ZonesFeature]