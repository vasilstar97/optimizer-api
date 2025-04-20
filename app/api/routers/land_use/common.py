
from lu_igi.models.land_use import LandUse

LU_MAPPING = {
  1: LandUse.RESIDENTIAL,
  2: LandUse.RECREATION,
  3: LandUse.SPECIAL,
  4: LandUse.INDUSTRIAL,
  5: LandUse.AGRICULTURE,
  6: LandUse.TRANSPORT,
  7: LandUse.BUSINESS,
  10: LandUse.RESIDENTIAL,
  11: LandUse.RESIDENTIAL,
  12: LandUse.RESIDENTIAL,
  13: LandUse.RESIDENTIAL,
#   15: LandUse.RESIDENTIAL,
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