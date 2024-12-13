from fastapi import APIRouter
import geopandas as gpd
from ...utils import decorators, const
from . import zoning_service, zoning_models

router = APIRouter(prefix='/zoning', tags=['Zoning'])

@router.get('/profiles')
def get_profiles() -> list[zoning_models.Profile]:
    return zoning_models.Profile

@router.post('/generate')
@decorators.gdf_to_geojson
def generate_zones(profile : zoning_models.Profile, blocks : zoning_models.BlocksModel, max_iter : int = 1_000, rate : float = 0.999) -> zoning_models.ZonesModel:
    blocks_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in blocks.features], const.DEFAULT_CRS)
    return zoning_service.generate_zoning(profile, blocks_gdf, max_iter, rate)