import json
import shapely
import geopandas as gpd
from loguru import logger
from blocksnet.preprocessing.blocks_generator import BlocksGenerator
from ...utils import api_client, const

def _fetch_project_geometry(project_scenario_id : int, token : str):
    scenario_info = api_client.get_scenario_by_id(project_scenario_id, token)
    project_id = scenario_info['project_id']
    project_info = api_client.get_project_by_id(project_id, token)
    project_geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(project_geometry_json)

def _fetch_water_objects(project_scenario_id : int, token : str):
    return None

def generate_blocks(project_scenario_id : int, roads_gdf : gpd.GeoDataFrame, token : str):
    
    logger.info('Fetching project geometry')
    project_geometry = _fetch_project_geometry(project_scenario_id, token)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=const.DEFAULT_CRS)

    local_crs = project_gdf.estimate_utm_crs()

    logger.info('Fetching water objects')
    water_gdf = _fetch_water_objects(project_scenario_id, token)
    
    logger.info('Initializing BlocksGenerator')
    bg = BlocksGenerator(project_gdf.to_crs(local_crs), roads_gdf.to_crs(local_crs), None, water_gdf)
    return bg.run()