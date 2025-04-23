import json
import shapely
import geopandas as gpd
import momepy
from loguru import logger
from ...utils import const, api_client
from lu_igi.preprocessing.graph import generate_adjacency_graph
from lu_igi.preprocessing.land_use import process_land_use
from lu_igi.optimization.optimizer import Optimizer
from lu_igi.models.land_use import LandUse
from blocksnet.preprocessing.blocks_generator import BlocksGenerator
from .common import LU_MAPPING, LU_SHARES

DEFAULT_CRS = 4326
MIN_INTERSECTION_SHARE = 0.3

LAND_USE_MAPPING = {
    1 : LandUse.RESIDENTIAL,
    2 : LandUse.RECREATION,
    3 : LandUse.SPECIAL,
    4 : LandUse.INDUSTRIAL,
    5 : LandUse.AGRICULTURE,
    6 : LandUse.TRANSPORT,
    7 : LandUse.BUSINESS,
    10 : LandUse.RESIDENTIAL,
    11 : LandUse.RESIDENTIAL,
    12 : LandUse.RESIDENTIAL,
    13 : LandUse.RESIDENTIAL,
}

def _get_profile_lu_shares(profile_id : int) -> dict[LandUse, float]:
    lu = LU_MAPPING[profile_id]
    return LU_SHARES[lu]

def _process_land_use(blocks_gdf : gpd.GeoDataFrame, zones_gdf : gpd.GeoDataFrame):
    logger.info('2. Processing blocks land use')
    zones_gdf.geometry = zones_gdf.buffer(0) # somehow fixes topology problems
    logger.info('2.1. Mapping functional_zone_type with ids')
    zones_gdf['zone'] = zones_gdf['functional_zone_type'].apply(lambda fzt : fzt['id'])
    logger.info('2.2. Intersecting land use with blocks')
    result_gdf = process_land_use(blocks_gdf, zones_gdf, LAND_USE_MAPPING, min_intersection_share=0.3)
    logger.success('2.3. Land use is processed successfully')
    return result_gdf

def _get_project_geometry(project_id : int, token):
    project_info = api_client.get_project_by_id(project_id, token)
    geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(geometry_json)

def _fetch_water_objects(project_id : int, token : str):
    return None

def _generate_blocks(project_id : int, roads_gdf : gpd.GeoDataFrame, token : str | None):

    local_crs = roads_gdf.crs

    logger.info('1. Generating blocks')
    logger.info('1.1. Fetching project geometry')
    project_geometry = _get_project_geometry(project_id, token)
    logger.info(project_geometry)
    project_gdf = gpd.GeoDataFrame(geometry=[project_geometry], crs=const.DEFAULT_CRS).to_crs(local_crs)
    project_gdf.geometry = project_gdf.geometry.buffer(-1)

    logger.info('1.2. Fetching water objects')
    water_gdf = _fetch_water_objects(project_id, token)
    
    logger.info('1.3. Initializing and running BlocksGenerator')
    roads_gdf = roads_gdf.explode(index_parts=False).reset_index(drop=True)
    roads_gdf.geometry = momepy.close_gaps(roads_gdf, 1)
    bg = BlocksGenerator(project_gdf, roads_gdf, None, water_gdf)
    blocks_gdf = bg.run()
    
    logger.success('1.4. Blocks are generated successfully')
    return blocks_gdf

def _get_buffer_size(blocks_gdf : gpd.GeoDataFrame, buffer_step = 5, max_buffer_size = 100):
    buffer_size = 0
    while buffer_size < max_buffer_size:
        union = blocks_gdf.geometry.buffer(buffer_size).unary_union
        if isinstance(union, shapely.Polygon):
            break
        buffer_size += buffer_step
    return buffer_size


def _optimize_land_use(profile_id : int, blocks_gdf : gpd.GeoDataFrame, max_iter : int):
    logger.info('3. Optimizing land use')

    buffer_size = _get_buffer_size(blocks_gdf)
    logger.info(f'3.1. Generating adjacency graph for buffer_size={buffer_size} and setting optimizer')
    graph = generate_adjacency_graph(blocks_gdf, buffer_size)
    optimizer = Optimizer(graph)

    logger.info('3.2. Getting profile land use shares')
    target_lu_shares = _get_profile_lu_shares(profile_id)
    blocks_ids = list(blocks_gdf.index)

    logger.info('3.3. Running the optimizer')
    result_df = optimizer.run(blocks_ids, target_lu_shares, n_eval=max_iter, verbose=False)

    logger.info('3.4. Expanding the result')
    result = optimizer.expand_result_df(result_df)
    
    logger.success('3.5. Land use is optimized successfully')
    return result

def generate_land_use(project_id : int, profile_id : int, user_gdf : gpd.GeoDataFrame, zones_gdf : gpd.GeoDataFrame, generate_blocks : bool, max_iter : int, token : str | None):

    logger.info('0. Preprocessing input')
    local_crs = zones_gdf.estimate_utm_crs()
    zones_gdf = zones_gdf.to_crs(local_crs)
    user_gdf = user_gdf.to_crs(local_crs)

    if generate_blocks:
        blocks_gdf = _generate_blocks(project_id, user_gdf, token)
    else:
        blocks_gdf = user_gdf.explode(index_parts=False).reset_index(drop=True)

    blocks_gdf = _process_land_use(blocks_gdf, zones_gdf)

    return _optimize_land_use(profile_id, blocks_gdf, max_iter)
