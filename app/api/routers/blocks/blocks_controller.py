from fastapi import APIRouter, Request, Depends
import pydantic_geojson as pg
import geopandas as gpd
from ...utils import decorators, auth, const
from . import blocks_models, blocks_service

router = APIRouter(prefix='/blocks', tags=['Blocks'])

@router.post('/generate')
@decorators.gdf_to_geojson
def generate_blocks(project_id : int, token : str = Depends(auth.verify_token), road_network : blocks_models.RoadNetworkModel | None = None) -> blocks_models.BlocksModel:
    if road_network is not None:
        road_network_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in road_network.features], const.DEFAULT_CRS)
    else:
        road_network_gdf = None
    return blocks_service.generate_blocks(project_id, token, road_network_gdf)