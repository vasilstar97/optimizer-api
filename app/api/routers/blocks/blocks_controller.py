from fastapi import APIRouter, Request, Depends
import pydantic_geojson as pg
import geopandas as gpd
from ...utils import decorators, auth, const
from . import blocks_models, blocks_service

router = APIRouter(prefix='/blocks', tags=['Blocks'])

@router.post('/generate')
@decorators.gdf_to_geojson
def generate_blocks(project_scenario_id : int, road_network : blocks_models.RoadNetworkModel, token : str = Depends(auth.verify_token)) -> blocks_models.BlocksModel:
    road_network_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in road_network.features], const.DEFAULT_CRS)
    return blocks_service.generate_blocks(project_scenario_id, road_network_gdf, token)