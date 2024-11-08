import json
import shapely
import geopandas as gpd
import random
from loguru import logger
from blocksnet.preprocessing.land_use_optimizer import LandUseOptimizer, LandUse
from ...utils import const
from .zoning_models import Profile

DEFAULT_CRS = 4326

def _get_profile_lu_shares(profile : Profile) -> dict[LandUse, float]: #FIXME remove randomness
    random_values = [random.random() for _ in range(len(LandUse))]
    total = sum(random_values)
    probabilities = [value / total for value in random_values]
    return dict(zip(LandUse, probabilities))

def generate_zoning(profile : Profile, blocks_gdf : gpd.GeoDataFrame, max_iter : int):

    local_crs = blocks_gdf.estimate_utm_crs()
    blocks_gdf = blocks_gdf.to_crs(local_crs)

    lu_shares = _get_profile_lu_shares(profile)
    
    logger.info('Initializing land use optimizer')
    luo = LandUseOptimizer(blocks_gdf)

    logger.info('Solving the optimization problem')
    best_X, best_value, _, _ = luo.run(lu_shares, max_iter=max_iter)
    logger.success(f'Problem solved, fit value equals {round(best_value,3)}')

    return luo.to_gdf(best_X)