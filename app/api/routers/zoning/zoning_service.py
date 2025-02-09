import json
import shapely
import geopandas as gpd
import random
from loguru import logger
from ...utils import const
from .zoning_models import Profile
from lu_igi.preprocessing.graph import generate_adjacency_graph
from lu_igi.optimization.optimizer import Optimizer
from lu_igi.optimization.problem import FitnessType
from lu_igi.models.land_use import LandUse

FITNESS_TYPES = [
    FitnessType.ADJACENCY_PENALTY, 
    FitnessType.PROBABILITY, 
    FitnessType.SHARE_MSE
]

DEFAULT_CRS = 4326

def _get_profile_lu_shares(profile : Profile) -> dict[LandUse, float]: #FIXME remove randomness
    random_values = [random.random() for _ in range(len(LandUse))]
    total = sum(random_values)
    probabilities = [value / total for value in random_values]
    return dict(zip(LandUse, probabilities))

def _generate_adjacency_graph(blocks_gdf : gpd.GeoDataFrame):
    blocks_gdf['land_use'] = None
    return generate_adjacency_graph(blocks_gdf)

def generate_zoning(profile : Profile, blocks_gdf : gpd.GeoDataFrame, max_iter : int, rate : float):

    local_crs = blocks_gdf.estimate_utm_crs()
    blocks_gdf = blocks_gdf.to_crs(local_crs)

    graph = _generate_adjacency_graph(blocks_gdf)
    optimizer = Optimizer(graph)

    target_lu_shares = _get_profile_lu_shares(profile)
    blocks_ids = list(blocks_gdf.index)

    results = optimizer.run(blocks_ids, target_lu_shares, FITNESS_TYPES, n_eval=max_iter, verbose=False)

    best_solutions = optimizer.best_solutions(results, FITNESS_TYPES)
    best_solution = best_solutions[FitnessType.SHARE_MSE]['X']

    blocks_gdf = optimizer.to_gdf(best_solution,blocks_ids,blocks_gdf.crs)
    blocks_gdf['land_use'] = blocks_gdf['assigned_land_use'].apply(lambda lu : lu.value)

    return blocks_gdf[['geometry', 'land_use']]