import json
from fastapi import APIRouter, Depends, HTTPException
import geopandas as gpd
from lu_igi.optimization.problem import FitnessType
from ...utils import const, auth
from . import land_use_models, land_use_service

router = APIRouter(prefix='/land_use', tags=['Land use'])

def process_result(result : list[dict]):
    
    def process_item(item : dict):
        gdf = item['gdf'].to_crs(const.DEFAULT_CRS)
        gdf['land_use'] = gdf['land_use'].apply(lambda lu : None if lu is None else lu.value)
        gdf['assigned_land_use'] = gdf['assigned_land_use'].apply(lambda lu : lu.value)
        return {
            'blocks': json.loads(gdf.to_json()),
            'fitness': {ft.value : item[ft.value] for ft in list(FitnessType)}
        }
    
    return [process_item(item) for item in result]

@router.post('/generate')
def generate_land_use(
        project_id : int,
        profile_id : int,
        roads :  land_use_models.RoadsFeatureCollection | None,
        blocks : land_use_models.BlocksFeatureCollection | None,
        zones : land_use_models.ZonesFeatureCollection, 
        max_iter : int = 1_000,
        token : str = Depends(auth.verify_token),
    ) -> list[land_use_models.LandUseResponseItem]:
    if blocks is not None:
        user_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in blocks.features], const.DEFAULT_CRS)
        generate_blocks = False
    elif roads is not None:
        user_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in roads.features], const.DEFAULT_CRS)
        generate_blocks = True
    else:
        raise HTTPException(400, 'Either blocks or roads must be provided in body')
    zones_gdf = gpd.GeoDataFrame.from_features([f.model_dump() for f in zones.features], const.DEFAULT_CRS)
    result = land_use_service.generate_land_use(project_id, profile_id, user_gdf, zones_gdf, generate_blocks, max_iter, token)
    return process_result(result)