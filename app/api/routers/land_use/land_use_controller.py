import json
from fastapi import APIRouter
import geopandas as gpd
from lu_igi.optimization.problem import FitnessType
from ...utils import decorators, const
from . import land_use_models, land_use_service

router = APIRouter(prefix='/land_use', tags=['Land use'])

@router.get('/profiles')
def get_profiles() -> list[land_use_models.Profile]:
    return land_use_models.Profile

def process_result(result : list[dict]):
    
    def process_item(item : dict):
        gdf = item['gdf'].to_crs(const.DEFAULT_CRS)
        gdf['land_use'] = gdf['land_use'].apply(lambda lu : lu.value)
        gdf['assigned_land_use'] = gdf['assigned_land_use'].apply(lambda lu : lu.value)
        return {
            'blocks': json.loads(gdf.to_json()),
            'fitness': {ft.value : item[ft.value] for ft in list(FitnessType)}
        }
    
    return [process_item(item) for item in result]

@router.post('/generate')
def generate_land_use(
        profile : land_use_models.Profile, 
        blocks : land_use_models.BlocksFeatureCollection, 
        zones : land_use_models.ZonesFeatureCollection, 
        n_results : int = 3,
        max_iter : int = 5_000,
    ) -> list[land_use_models.LandUseResponseItem]:
    blocks_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in blocks.features], const.DEFAULT_CRS)
    zones_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in zones.features], const.DEFAULT_CRS)
    result = land_use_service.generate_land_use(profile, blocks_gdf, zones_gdf, max_iter)[:n_results]
    return process_result(result)
