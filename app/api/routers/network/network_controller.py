import geopandas as gpd
from fastapi import APIRouter, Depends
from ...utils import decorators, auth
from . import network_service, network_models

router = APIRouter(prefix='/network', tags=['Network'])

@router.post('/generate')
@decorators.gdf_to_geojson
def generate_network(project_scenario_id : int, token : str = Depends(auth.verify_token)) -> network_models.RoadNetworkModel:
    return network_service.generate_network(project_scenario_id, token)
        
    