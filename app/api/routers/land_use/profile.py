
from lu_igi.models.land_use import LandUse
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

LU_MAPPING = {
  Profile.RESIDENTIAL_INDIVIDUAL: LandUse.RESIDENTIAL,
  Profile.RESIDENTIAL_LOWRISE: LandUse.RESIDENTIAL,
  Profile.RESIDENTIAL_MIDRISE: LandUse.RESIDENTIAL,
  Profile.RESIDENTIAL_MULTISTOREY: LandUse.RESIDENTIAL,
  Profile.BUSINESS: LandUse.BUSINESS,
  Profile.RECREATION: LandUse.RECREATION,
  Profile.SPECIAL: LandUse.SPECIAL,
  Profile.INDUSTRIAL: LandUse.INDUSTRIAL,
  Profile.AGRICULTURE: LandUse.AGRICULTURE,
  Profile.TRANSPORT: LandUse.TRANSPORT
}

LU_SHARES = {
  LandUse.RESIDENTIAL : {
      LandUse.RESIDENTIAL: 0.5,
      LandUse.BUSINESS: 0.1,
      LandUse.RECREATION: 0.1,
      LandUse.TRANSPORT: 0.1,
      LandUse.AGRICULTURE: 0.05,
      LandUse.SPECIAL: 0.05,
  },
  LandUse.INDUSTRIAL : {
      LandUse.INDUSTRIAL: 0.5,
      LandUse.BUSINESS: 0.1,
      LandUse.RECREATION: 0.05,
      LandUse.TRANSPORT: 0.1,
      LandUse.AGRICULTURE: 0.05,
      LandUse.SPECIAL: 0.05,
  },
  LandUse.BUSINESS : {
      LandUse.RESIDENTIAL: 0.1,
      LandUse.BUSINESS: 0.5,
      LandUse.RECREATION: 0.1,
      LandUse.TRANSPORT: 0.1,
      LandUse.AGRICULTURE: 0.05,
      LandUse.SPECIAL: 0.05,
  },
  LandUse.RECREATION : {
      LandUse.RESIDENTIAL: 0.2,
      LandUse.BUSINESS: 0.1,
      LandUse.RECREATION: 0.5,
      LandUse.TRANSPORT: 0.05,
      LandUse.AGRICULTURE: 0.1,
  },
  LandUse.TRANSPORT : {
      LandUse.INDUSTRIAL: 0.1,
      LandUse.BUSINESS: 0.05,
      LandUse.RECREATION: 0.05,
      LandUse.TRANSPORT: 0.5,
      LandUse.AGRICULTURE: 0.05,
      LandUse.SPECIAL: 0.05,
  },
  LandUse.AGRICULTURE : {
      LandUse.RESIDENTIAL: 0.1,
      LandUse.INDUSTRIAL: 0.1,
      LandUse.BUSINESS: 0.05,
      LandUse.RECREATION: 0.1,
      LandUse.TRANSPORT: 0.05,
      LandUse.AGRICULTURE: 0.5,
      LandUse.SPECIAL: 0.05,
  },
  LandUse.SPECIAL : {
      LandUse.RESIDENTIAL: 0.01,
      LandUse.INDUSTRIAL: 0.1,
      LandUse.BUSINESS: 0.05,
      LandUse.RECREATION: 0.05,
      LandUse.TRANSPORT: 0.05,
      LandUse.AGRICULTURE: 0.05,
      LandUse.SPECIAL: 0.5,
  }
}