import json
import shapely
import geopandas as gpd
import random
from loguru import logger
from ...utils import const
from .land_use_models import Profile
from lu_igi.preprocessing.graph import generate_adjacency_graph
from lu_igi.preprocessing.land_use import process_land_use
from lu_igi.optimization.optimizer import Optimizer
from lu_igi.optimization.problem import FitnessType
from lu_igi.models.land_use import LandUse

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

def _get_profile_lu_shares(profile : Profile) -> dict[LandUse, float]: #FIXME remove randomness
    random_values = [random.random() for _ in range(len(LandUse))]
    total = sum(random_values)
    probabilities = [value / total for value in random_values]
    return dict(zip(LandUse, probabilities))

def _process_land_use(blocks_gdf : gpd.GeoDataFrame, zones_gdf : gpd.GeoDataFrame):
    zones_gdf.geometry = zones_gdf.buffer(0) # somehow fixes topology problems
    zones_gdf['zone'] = zones_gdf['functional_zone_type'].apply(lambda fzt : fzt['id'])
    return process_land_use(blocks_gdf, zones_gdf, LAND_USE_MAPPING, min_intersection_share=0.3)

def generate_land_use(profile : Profile, blocks_gdf : gpd.GeoDataFrame, zones_gdf : gpd.GeoDataFrame, max_iter : int):

    local_crs = blocks_gdf.estimate_utm_crs()
    blocks_gdf = blocks_gdf.to_crs(local_crs)
    zones_gdf = zones_gdf.to_crs(local_crs)

    blocks_gdf = _process_land_use(blocks_gdf, zones_gdf)
    graph = generate_adjacency_graph(blocks_gdf)
    optimizer = Optimizer(graph)

    target_lu_shares = _get_profile_lu_shares(profile)
    blocks_ids = list(blocks_gdf.index)

    result_df = optimizer.run(blocks_ids, target_lu_shares, n_eval=max_iter, verbose=False)
    return optimizer.expand_result_df(result_df)